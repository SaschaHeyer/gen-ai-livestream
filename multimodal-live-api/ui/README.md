# Multimodal Live API Demo with Web Interface

This project demonstrates a bidirectional audio conversation with Google's Gemini 2.0 Flash Live API integrated into a web interface. It features a client-side audio handling approach where all audio recording and playback happens in the browser.

## Project Structure

- `server.py` - WebSocket server that connects to Gemini AI
- `audio-client.js` - JavaScript client for handling audio in the browser
- `index.html` - Web interface with IKEA-inspired design
- `requirements.txt` - Python dependencies

## Key Features

- **Audio handled entirely on the client side** - No need for server-side audio libraries
- **Bidirectional audio conversations** with Gemini Live AI
- **Session persistence** with session ID tracking
- **Responsive UI**
- **Real-time transcription** of both input and output speech

## Setup Instructions

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

No special audio libraries needed! Just standard WebSocket and Gemini dependencies.

### 2. Start the WebSocket Server

```bash
python server.py
```

The server will start and listen for WebSocket connections on port 8765.

### 3. Open the Web Interface

Open `index.html` in your web browser. You can use any web server, or simply open the file directly:

```bash
# Using Python's built-in HTTP server
python -m http.server 8000
```

Then navigate to `http://localhost:8000/index.html` in your browser.

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
- **API Keys**: Ensure your Google API credentials are properly configured in `server.py`
