# ADK + Vertex AI Live API Demo

A demonstration project showcasing how to build real-time, streaming multimodal experiences using Google's Agent Development Kit (ADK) with the Vertex AI Live API.

## Overview

This repository contains a complete implementation of a multimodal assistant that can:

- Process real-time audio input from a microphone
- Analyze video input from webcam or screen sharing
- Stream responses as audio and text
- Showcase function calling capabilities with the ADK

The project demonstrates how to go beyond the standard ADK CLI by creating a custom server implementation that integrates directly with the Live API streaming functionality.

## Repository Structure

```
- adk_audio_to_audio.py      # Standalone ADK audio assistant example
- app/
  - client/                  # Frontend web client
    - audio-client.js        # Audio WebSocket client base class
    - multimodal-client.js   # Extended client with video capabilities
    - multimodal.html        # Web UI for the demo
  - server/                  # Backend server implementation
    - common.py              # Shared utilities and mock functions
    - multimodal_server_adk.py  # ADK integration with WebSockets
    - start_servers.sh       # Server startup script
    - DEPLOYMENT.md          # Deployment instructions
```

## Key Features

- **Bidirectional Audio Streaming**: Real-time voice conversation with the Gemini model
- **Video Analysis**: Process webcam or screen sharing video frames
- **WebSocket Communication**: Low-latency bidirectional communication
- **Function Calling**: Demonstration of ADK tool integration with a mock order status function
- **Full ADK Integration**: Uses ADK's `LiveRequestQueue` and `Runner` for communication with Gemini

## Getting Started

### Prerequisites

- Google Cloud project with API access
- Python 3.9+
- Node.js for client development (if modifying)
- Google ADK installed (`pip install google-adk`)
- PyAudio for audio processing

### Installation

1. Clone this repository
   ```
   git clone https://github.com/SaschaHeyer/gen-ai-livestream.git
   cd gen-ai-livestream/agents/agent-development-kit/live-api
   ```

2. Install server dependencies
   ```
   cd app/server
   pip install -r requirements.txt
   ```

3. Start the server
   ```
   ./start_servers.sh
   ```

4. Open the client in your browser
   ```
   open app/client/multimodal.html
   ```

## Deployment

This project includes detailed instructions for deploying to Google Cloud Run with WebSocket support and session affinity. See [DEPLOYMENT.md](app/server/DEPLOYMENT.md) for complete deployment instructions.

Key deployment features:
- Cloud Run with WebSocket support via annotations
- Session affinity for stable connections
- Docker container configuration
- Artifact Registry integration

## How It Works

The implementation uses several key technologies:

1. **ADK Integration**: The server uses ADK's `LiveRequestQueue` to stream audio and video to Gemini
2. **WebSockets**: Bidirectional communication between client and server
3. **Media Processing**: Browser APIs capture and process audio/video
4. **Async Processing**: Python's asyncio powers the server-side concurrency

### Server Architecture

The server manages several concurrent tasks:
- WebSocket connection handling
- Audio processing and streaming
- Video frame processing
- Response handling from Gemini

### Client Implementation

The client handles:
- Audio recording and playback
- Video capture (webcam and screen sharing)
- WebSocket communication
- UI updates and transcription display

## Additional Resources

- [Original Article: Going Beyond the ADK CLI](https://github.com/SaschaHeyer/gen-ai-livestream/tree/main/agents/agent-development-kit/live-api/app)
- [Full Project with Additional Features](https://github.com/SaschaHeyer/gen-ai-livestream/tree/main/multimodal-live-api/ui)

## License
This project is licensed under the MIT License.
