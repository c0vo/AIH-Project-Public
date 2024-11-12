import os
import uuid
import json
import io
import queue
import threading
import base64
import numpy as np
import time
from flask_socketio import SocketIO, emit
from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv
from google.cloud import dialogflowcx_v3beta1, texttospeech, speech, translate_v2
from google.oauth2 import service_account
from werkzeug.utils import secure_filename
from google.cloud import aiplatform
from vertexai.preview.generative_models import GenerativeModel, Part
from vertexai.preview.generative_models import HarmCategory, HarmBlockThreshold
from engineio.async_drivers import threading as async_threading
from collections import defaultdict


app = Flask(__name__)
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    async_mode='threading',
    ping_timeout=60,
    ping_interval=25
)
load_dotenv()

# Create a queue for the audio chunks
audio_queue = queue.Queue()

# Dialogflow CX configuration
PROJECT_ID = "<REPLACE WITH YOUR PROJECT ID>"
LOCATION_ID = "asia-southeast1"
AGENT_ID = "<REPLACE WITH YOUR AGENT ID>"
AGENT = f"projects/{PROJECT_ID}/locations/{LOCATION_ID}/agents/{AGENT_ID}"
LANGUAGE_CODE = "en-us"

# Load credentials from environment variable
credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
print("Credentials JSON:", credentials_json[:100] + "...") # Print first 100 chars for debugging

if credentials_json:
    credentials_dict = json.loads(credentials_json)
    credentials = service_account.Credentials.from_service_account_info(credentials_dict)
else:
    raise ValueError("GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable not set")

client_options = None
agent_components = dialogflowcx_v3beta1.AgentsClient.parse_agent_path(AGENT)
location_id = agent_components["location"]
if location_id != "global":
    api_endpoint = f"{location_id}-dialogflow.googleapis.com:443"
    client_options = {"api_endpoint": api_endpoint}

# Create clients with the credentials
session_client = dialogflowcx_v3beta1.SessionsClient(credentials=credentials, client_options=client_options)
agents_client = dialogflowcx_v3beta1.AgentsClient(credentials=credentials, client_options=client_options)

# Initialize Vertex AI
aiplatform.init(project=PROJECT_ID, location=LOCATION_ID, credentials=credentials)

# Intialize TTS, STT and language detection
tts_client = texttospeech.TextToSpeechClient(credentials=credentials)
translate_client = translate_v2.Client(credentials=credentials)

# Create a 'temp' folder in the current working directory
current_dir = os.path.dirname(os.path.abspath(__file__))
temp_folder = os.path.join(current_dir, 'temp')
if not os.path.exists(temp_folder):
    os.makedirs(temp_folder)

# Set the upload folder to the newly created 'temp' folder
app.config['UPLOAD_FOLDER'] = temp_folder

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Store client-specific queues and threads
client_queues = {}
client_threads = {}
active_sessions = defaultdict(bool)

@app.route('/')
def index():
    return render_template('index.html')

# Dictionary to store session IDs for each user
user_sessions = {}

@app.route('/chatbot', methods=['POST'])
def chatbot():
    user_ip = request.remote_addr  # Use IP address as user identifier
    
    # Create or get session ID for this user
    if user_ip not in user_sessions:
        user_sessions[user_ip] = str(uuid.uuid4())
    
    session_id = user_sessions[user_ip]
    user_input = request.form.get('data')
    file = request.files.get('file')
    
    response = ""

    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            with open(filepath, 'rb') as image_file:
                image_data = image_file.read()

            response = analyze_image_for_scam(image_data, user_input)
            
            os.remove(filepath)
        except Exception as e:
            print(f"Error processing image: {e}")
            response += f'Error processing image: {str(e)}'
    
    elif user_input:
        try:
            response = get_response(user_input, session_id)
        except Exception as e:
            print(f"Error processing text: {e}")
            response += f'Error processing text: {str(e)}'
    else:
        response = "No input received. Please provide a message or upload an image."

    print(f"User IP: {user_ip}")
    print(f"Session ID: {session_id}")
    print(f"Chatbot Response: {response}")
    
    return jsonify({"response": True, "message": response})

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def analyze_image_for_scam(image_data, user_prompt=""):
    model = GenerativeModel("gemini-pro-vision")
    image_part = Part.from_data(image_data, mime_type="image/jpeg")

    scam_analysis = f"""
    Analyze this image for potential scam or phishing indicators. 
    Classify the likelihood of this being a scam/phishing attempt as one of these:
    "VERY UNLIKELY to be a scam.", "UNLIKELY to be a scam.", "LIKELY to be a scam.", or "VERY LIKELY to be a scam."
    
    After classification, explain your reasoning (in clear, succinct point forms) using contextual information (either provided by the user or found in the image) or the contents of the image itself.
    
    User context (if any): {user_prompt}
    
    Format your response as follows:
    Classification: [Your classification]
    Explanation: [Your explanation]
    """
    
    safety_settings = {
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    }
    
    try:
        response = model.generate_content(
            [scam_analysis, image_part],
            safety_settings=safety_settings
        )
        
        if response.text:
            return response.text
        else:
            return "The analysis could not generate a response. This may indicate an issue with the image or the analysis process. Please try again."
    
    except Exception as e:
        return f"An error occurred during image analysis: {str(e)}"

def get_response(text, session_id):
    session_path = f"{AGENT}/sessions/{session_id}"
    
    text_input = dialogflowcx_v3beta1.TextInput(text=text)
    query_input = dialogflowcx_v3beta1.QueryInput(text=text_input, language_code=LANGUAGE_CODE)
    request_payload = dialogflowcx_v3beta1.DetectIntentRequest(
        session=session_path, query_input=query_input
    )
    
    try:
        response = session_client.detect_intent(request=request_payload)
        print(f"Full Dialogflow response: {response}")
        
        response_messages = [
            " ".join(msg.text.text) for msg in response.query_result.response_messages
        ]
        return ' '.join(response_messages)
    except Exception as e:
        print(f"Error in get_response: {e}")
        raise


@app.route('/text-to-speech', methods=['POST'])
def text_to_speech():
    try:
        text = request.json.get('text')
        if not text:
            return jsonify({"error": "No text provided"}), 400

        # Detect language
        result = translate_client.detect_language(text)
        detected_language = result["language"]
        print(f"Detected Language : {detected_language}")
        
        # Configure voice based on detected language
        voice_config = {
            'en': ('en-US', texttospeech.SsmlVoiceGender.NEUTRAL),   # English
            'ta': ('ta-IN', texttospeech.SsmlVoiceGender.NEUTRAL),   # Tamil
            'zh-CN': ('cmn-CN', texttospeech.SsmlVoiceGender.NEUTRAL),  # Mandarin (Simplified Chinese, China)
            'hi': ('hi-IN', texttospeech.SsmlVoiceGender.NEUTRAL),   # Hindi (India)
        }
        
        language_code, voice_gender = voice_config.get(
            detected_language, 
            ('en-US', texttospeech.SsmlVoiceGender.NEUTRAL)  # default to English
        )

        # Configure audio
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            ssml_gender=voice_gender
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        # Perform text-to-speech
        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        # Use BytesIO to return the audio content directly
        audio_output = io.BytesIO(response.audio_content)
        audio_output.seek(0)  # Move to the beginning of the BytesIO buffer

        # Send the audio content as a response
        return send_file(
            audio_output,
            mimetype='audio/mp3',
            as_attachment=True,
            download_name='response.mp3'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

def process_audio_stream(responses, session_id):
    """
    Process streaming responses from Google Speech-to-Text API
    and emit results through Socket.IO
    """
    last_final_time = time.time()
    SILENCE_TIMEOUT = 2.0  # Time in seconds to wait after final transcript

    try:
        for response in responses:
            if not response.results:
                continue

            result = response.results[0]
            if not result.alternatives:
                continue

            current_time = time.time()
            
            if result.is_final:
                transcript = result.alternatives[0].transcript
                print(f"Final transcript: {transcript}")
                socketio.emit('final_transcript', {
                    'transcript': transcript,
                    'session_id': session_id
                })
                last_final_time = current_time
                
            else:
                transcript = result.alternatives[0].transcript
                print(f"Interim transcript: {transcript}")
                socketio.emit('interim_transcript', {
                    'transcript': transcript,
                    'session_id': session_id
                })
                
            # Check for silence timeout
            if current_time - last_final_time > SILENCE_TIMEOUT:
                print(f"Silence detected for {SILENCE_TIMEOUT} seconds, ending stream")
                socketio.emit('end_stream', {'session_id': session_id})  # Send end signal to client
                break

    except Exception as e:
        print(f"Error processing stream: {str(e)}")
        socketio.emit('error', {
            'message': 'Error processing audio stream',
            'session_id': session_id
        })

def audio_streaming_thread(client_id, session_id):
    """Background thread to handle audio streaming for a specific client"""
    try:
        if client_id not in client_queues:
            return
            
        client = speech.SpeechClient(credentials=credentials)
        
        def audio_generator():
            while active_sessions[client_id]:
                try:
                    chunk = client_queues[client_id].get(timeout=5)
                    if chunk is None:
                        break
                    if isinstance(chunk, (bytes, bytearray)):
                        yield speech.StreamingRecognizeRequest(audio_content=chunk)
                except queue.Empty:
                    continue

        streaming_config = speech.StreamingRecognitionConfig(
            config=speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=48000,
                language_code='en-US',
                enable_automatic_punctuation=True,
            ),
            interim_results=True
        )

        print(f"Starting transcription for client {client_id}")
        
        responses = client.streaming_recognize(
            config=streaming_config,
            requests=audio_generator()
        )

        for response in responses:
            if not active_sessions[client_id]:
                break
                
            if not response.results:
                continue

            result = response.results[0]
            if not result.alternatives:
                continue

            transcript = result.alternatives[0].transcript

            if result.is_final:
                socketio.emit('final_transcript', {
                    'transcript': transcript,
                    'session_id': session_id
                }, room=client_id)
            else:
                socketio.emit('interim_transcript', {
                    'transcript': transcript,
                    'session_id': session_id
                }, room=client_id)

    except Exception as e:
        print(f"Error in streaming thread: {str(e)}")
        socketio.emit('error', {
            'message': f'Error processing audio: {str(e)}',
            'session_id': session_id
        }, room=client_id)
    
    finally:
        print(f"Stream ended for client {client_id}")
        socketio.emit('end_stream', {'session_id': session_id}, room=client_id)
        active_sessions[client_id] = False

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    client_id = request.sid
    print(f"Client connected: {client_id}")
    client_queues[client_id] = queue.Queue()
    emit('connection_response', {'status': 'connected', 'client_id': client_id})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    client_id = request.sid
    print(f"Client disconnected: {client_id}")
    
    # Clean up client resources
    if client_id in active_sessions:
        active_sessions[client_id] = False
    
    if client_id in client_queues:
        # Signal thread to stop
        client_queues[client_id].put(None)
        del client_queues[client_id]
    
    if client_id in client_threads:
        client_threads[client_id].join(timeout=1)
        del client_threads[client_id]

@socketio.on('start_stream')
def handle_start_stream(data):
    """Handle the start of audio streaming"""
    try:
        client_id = request.sid
        session_id = data.get('session_id', str(uuid.uuid4()))
        print(f"Starting stream for client {client_id}, session {session_id}")
        
        # Clear any existing audio in the queue
        if client_id in client_queues:
            while not client_queues[client_id].empty():
                client_queues[client_id].get()
        
        active_sessions[client_id] = True
        
        # Start processing thread for this client
        thread = threading.Thread(
            target=audio_streaming_thread,
            args=(client_id, session_id)
        )
        thread.daemon = True
        thread.start()
        
        client_threads[client_id] = thread
        
        emit('stream_started', {
            'status': 'success',
            'session_id': session_id,
            'client_id': client_id
        })
        
    except Exception as e:
        print(f"Error starting stream: {str(e)}")
        emit('error', {
            'message': f'Error starting audio stream: {str(e)}',
            'session_id': session_id
        })

@socketio.on('stream_audio')
def handle_audio_chunk(data):
    """Handle incoming audio chunks"""
    try:
        client_id = request.sid
        audio_chunk = data.get('audio')
        
        if client_id in client_queues and audio_chunk:
            client_queues[client_id].put(audio_chunk)
        
    except Exception as e:
        print(f"Error handling audio chunk: {str(e)}")

@socketio.on('end_stream')
def handle_end_stream():
    """Handle the end of audio streaming"""
    try:
        client_id = request.sid
        if client_id in active_sessions:
            active_sessions[client_id] = False
        
        if client_id in client_queues:
            while not client_queues[client_id].empty():
                client_queues[client_id].get()
            client_queues[client_id].put(None)
        
    except Exception as e:
        print(f"Error ending stream: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False,
        allow_unsafe_werkzeug=True
    )