export class AudioHandler {
    constructor() {
        this.socket = io();
        this.voiceButton = document.getElementById('voiceButton');
        this.messageInput = document.getElementById('userinput');
        this.sessionId = crypto.randomUUID();
        this.isRecording = false;
        this.mediaRecorder = null;
        this.audioContext = null;
        this.audioInput = null;
        this.processor = null;
    }

    initialize() {
        this.setupSocketListeners();
        this.setupVoiceButton();
    }

    setupSocketListeners() {
        this.socket.on('interim_transcript', (data) => {
            if (data.session_id === this.sessionId) {
                this.messageInput.value = data.transcript;
            }
        });

        this.socket.on('final_transcript', (data) => {
            if (data.session_id === this.sessionId) {
                this.messageInput.value = data.transcript;
            }
        });

        this.socket.on('end_stream', (data) => {
            if (data.session_id === this.sessionId) {
                console.log('Stream ended (manual or auto)');
                this.stopRecording();
            }
        });
    }

    setupVoiceButton() {
        this.voiceButton.addEventListener('click', () => {
            if (!this.isRecording) {
                this.startRecording();
            } else {
                this.stopRecording();
            }
        });
    }

    async startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    sampleRate: 48000,
                    sampleSize: 16
                }
            });

            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 48000
            });

            this.audioInput = this.audioContext.createMediaStreamSource(stream);
            this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);

            this.audioInput.connect(this.processor);
            this.processor.connect(this.audioContext.destination);

            this.processor.onaudioprocess = (e) => {
                if (this.isRecording) {
                    const inputData = e.inputBuffer.getChannelData(0);
                    const pcmData = new Int16Array(inputData.length);
                    for (let i = 0; i < inputData.length; i++) {
                        pcmData[i] = Math.min(1, Math.max(-1, inputData[i])) * 0x7FFF;
                    }
                    
                    this.socket.emit('stream_audio', {
                        audio: pcmData.buffer,
                        session_id: this.sessionId
                    });
                }
            };

            this.socket.emit('start_stream', { session_id: this.sessionId });
            this.isRecording = true;
            this.voiceButton.querySelector('svg').style.stroke = '#2563eb';

        } catch (error) {
            console.error('Error accessing microphone:', error);
        }
    }

    stopRecording() {
        if (this.isRecording) {
            this.isRecording = false;
            this.voiceButton.querySelector('svg').style.stroke = 'currentColor';
            
            if (this.processor) {
                this.processor.disconnect();
                this.audioInput.disconnect();
            }
            if (this.audioContext) {
                this.audioContext.close();
            }
            
            this.socket.emit('end_stream');
        }
    }

    async playAudio(text) {
        try {
            const response = await fetch('/text-to-speech', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text: text })
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const audioBlob = await response.blob();
            const audioUrl = URL.createObjectURL(audioBlob);

            if (window.audioPlayer) {
                window.audioPlayer.pause();
                URL.revokeObjectURL(window.audioPlayer.src);
            }

            window.audioPlayer = new Audio(audioUrl);
            window.audioPlayer.play();
        } catch (error) {
            console.error('Error playing audio:', error);
        }
    }
}