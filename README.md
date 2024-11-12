## Features

- Real-time chat interface
- Voice input/output capabilities
- Image analysis for scam detection
- Multi-language support
- Real-time audio streaming
- Support for various file uploads

## Prerequisites

- Python 3.7+
- Google Cloud Platform account
- Google Cloud project with the following APIs enabled:
  - Dialogflow CX API
  - Cloud Text-to-Speech API
  - Cloud Speech-to-Text API
  - Cloud Translation API
  - Vertex AI API
- Google Cloud service account with appropriate permissions

## Setup Instructions

1. **Clone the repository**
```bash
git clone <repository-url>
cd <repository-name>
```

2. **Create and activate virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install required packages**
```bash
pip install -r requirements.txt
```

The requirements.txt includes all necessary packages including:
- Flask and Flask-SocketIO for web server and real-time communication
- Google Cloud services SDKs
- Eventlet for improved websocket performance
- Gunicorn for production deployment
- Other supporting packages

4. **Configure Google Cloud Credentials**

Create a `.env` file in the project root with your Google Cloud service account credentials. Replace the values with your own project details:

```plaintext
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type": "service_account", "project_id": "YOUR_PROJECT_ID", "private_key_id": "YOUR_PRIVATE_KEY_ID", "private_key": "YOUR_PRIVATE_KEY", "client_email": "YOUR_CLIENT_EMAIL", "client_id": "YOUR_CLIENT_ID", ...}
```

5. **Update Project Configuration**

In `main.py`, update the following variables with your Google Cloud project details:
```python
PROJECT_ID = "your-project-id"
LOCATION_ID = "your-location-id"  # e.g., "asia-southeast1"
AGENT_ID = "your-agent-id"
```

6. **Create Required Directories**
```bash
mkdir temp
```

## Running the Application

### Development
Start the server in development mode:
```bash
python main.py
```

### Production
For production deployment, use Gunicorn:
```bash
gunicorn --worker-class eventlet -w 1 main:app
```

The application will be available at `http://localhost:8080` by default.

## Project Structure

```
.
├── main.py              # Main application file
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (create this)
├── .gitignore          # Git ignore file
├── temp/               # Temporary file storage
└── templates/          # HTML templates (not shown in files)
```

## Environment Requirements

The application has been tested with the following package versions:
- Flask 3.0.3
- Flask-SocketIO 5.4.1
- google-cloud-aiplatform 1.67.1
- google-cloud-dialogflow-cx 1.35.0
- google-cloud-speech 2.28.0
- google-cloud-texttospeech 2.17.2
- google-cloud-translate 3.16.0
- python-dotenv 1.0.1
- vertexai 1.67.1

For a complete list of dependencies and their versions, see `requirements.txt`.

## Important Notes

1. The application uses environment variables for configuration. Make sure all required variables are set before running.
2. The temp directory is used for temporary file storage. Ensure it exists and has appropriate permissions.
3. This application uses websockets for real-time communication. Ensure your deployment environment supports this.
4. The default port is 8080, but can be modified through the PORT environment variable.
