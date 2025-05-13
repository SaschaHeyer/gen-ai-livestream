# Multimodal Live API with Gemini: Two Approaches

This project demonstrates bidirectional audio conversations with Google's Gemini 2.0 Flash Live API integrated into a web interface. It features a client-side audio handling approach where all audio recording and playback happens in the browser.

The project showcases **two different approaches** to implementing the same functionality:

1. **Google ADK** (Agent Development Kit) - Using the higher-level agent-based framework
2. **Direct LiveAPI** - Using the lower-level Gemini Live API directly

## Project Structure

- `server/common.py` - Shared components and utilities used by both implementations
- `server/server_adk.py` - Server implementation using Google ADK
- `server/server.py` - Server implementation using Gemini LiveAPI directly
- `client/audio-client.js` - JavaScript client for handling audio in the browser
- `client/index.html` - Web interface with IKEA-inspired design
- `server/requirements.txt` - Python dependencies

## Key Features

- **Two implementation approaches** for comparison and learning
- **Audio handled entirely on the client side** - No need for server-side audio libraries
- **Bidirectional audio conversations** with Gemini Live AI
- **Function calling** for order status lookup
- **Interruption detection** (interrupt the AI while it's speaking)
- **Session persistence** with session ID tracking
- **Responsive UI**
- **Real-time transcription** of both input and output speech

## Setup Instructions

### 1. Install Python Dependencies

```bash
pip install -r server/requirements.txt
```

No special audio libraries needed! Just standard WebSocket and Gemini dependencies.

### 2. Start the WebSocket Server

To run with the ADK implementation:
```bash
python server/server_adk.py
```

To run with the LiveAPI implementation:
```bash
python server/server.py
```

The server will start and listen for WebSocket connections on port 8765.

### 3. Open the Web Interface

Open `client/index.html` in your web browser. You can use any web server, or simply open the file directly:

```bash
# Using Python's built-in HTTP server
python -m http.server 8000
```

Then navigate to `http://localhost:8000/client/index.html` in your browser.

## Using the Application

1. Click the microphone button in the chat interface to start recording
2. Speak into your microphone
3. Click the button again to stop recording and send the audio to Gemini
4. Gemini will respond with audio that plays automatically
5. The conversation will continue back and forth
6. You can see the session ID at the top of the chat window, showing persistence

## Technologies Used

- **Python**
  - WebSockets for real-time communication
  - Google Generative AI library for Gemini integration
  - Google ADK for agent-based implementation

- **JavaScript**
  - Web Audio API for capturing and playing audio
  - WebSockets for communication with the server
  - Modern JavaScript (ES6+) for the client implementation

- **HTML/CSS**
  - Tailwind CSS for the UI
  - Responsive design for different screen sizes

## Troubleshooting

- **Microphone Access**: Ensure your browser has permission to access your microphone
- **WebSocket Connection**: Check that the server is running and accessible (default: ws://localhost:8765)
- **Audio Issues**: Verify that your microphone and speakers are working correctly