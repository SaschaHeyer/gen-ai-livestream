import asyncio
import json
import base64
import logging
import os
import traceback

# Import Google ADK components
from google.adk.agents import Agent, LiveRequestQueue
from google.adk.runners import Runner
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Import common components
from common import (
    BaseWebSocketServer,
    logger,
    MODEL,
    VOICE_NAME,
    SEND_SAMPLE_RATE,
    SYSTEM_INSTRUCTION,
    get_order_status,
)

# Function tool for order status
def order_status_tool(order_id: str):
    """Get the current status and details of an order.

    Args:
        order_id: The order ID to look up.

    Returns:
        Dictionary containing order status details
    """
    return get_order_status(order_id)


class MultimodalADKServer(BaseWebSocketServer):
    """WebSocket server implementation for multimodal input (audio + video) using Google ADK."""

    def __init__(self, host="0.0.0.0", port=8765):
        super().__init__(host, port)

        # Initialize ADK components
        self.agent = Agent(
            name="customer_service_agent",
            model=MODEL,
            instruction=SYSTEM_INSTRUCTION,
            tools=[order_status_tool],
        )

        # Create session service
        self.session_service = InMemorySessionService()

    async def process_audio(self, websocket, client_id):
        """Process audio and video from the client using ADK."""
        # Store reference to client
        self.active_clients[client_id] = websocket

        # Create session for this client
        session = self.session_service.create_session(
            app_name="multimodal_assistant",
            user_id=f"user_{client_id}",
            session_id=f"session_{client_id}",
        )

        # Create runner
        runner = Runner(
            app_name="multimodal_assistant",
            agent=self.agent,
            session_service=self.session_service,
        )

        # Create live request queue
        live_request_queue = LiveRequestQueue()

        # Create run config with audio settings
        run_config = RunConfig(
            streaming_mode=StreamingMode.BIDI,
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=VOICE_NAME
                    )
                )
            ),
            response_modalities=["AUDIO"],
            output_audio_transcription=types.AudioTranscriptionConfig(),
            input_audio_transcription=types.AudioTranscriptionConfig(),
        )

        # Queues for audio and video data from the client
        audio_queue = asyncio.Queue()
        video_queue = asyncio.Queue()

        async with asyncio.TaskGroup() as tg:
            # Task to process incoming WebSocket messages
            async def handle_websocket_messages():
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if data.get("type") == "audio":
                            # Decode base64 audio data
                            audio_bytes = base64.b64decode(data.get("data", ""))
                            # Put audio in queue for processing
                            await audio_queue.put(audio_bytes)
                        elif data.get("type") == "video":
                            # Decode base64 video frame
                            video_bytes = base64.b64decode(data.get("data", ""))
                            # Get video mode metadata if available
                            video_mode = data.get("mode", "webcam")  # Default to webcam if not specified
                            # Put video frame in queue for processing with metadata
                            await video_queue.put({
                                "data": video_bytes,
                                "mode": video_mode
                            })
                        elif data.get("type") == "end":
                            # Client is done sending audio for this turn
                            logger.info("Received end signal from client")
                        elif data.get("type") == "text":
                            # Handle text messages (not implemented in this simple version)
                            logger.info(f"Received text: {data.get('data')}")
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON message received")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")

            # Task to process and send audio to Gemini via ADK
            async def process_and_send_audio():
                while True:
                    data = await audio_queue.get()

                    # Send the audio data to Gemini through ADK's LiveRequestQueue
                    live_request_queue.send_realtime(
                        types.Blob(
                            data=data,
                            mime_type=f"audio/pcm;rate={SEND_SAMPLE_RATE}",
                        )
                    )

                    audio_queue.task_done()

            # Task to process and send video frames to Gemini via ADK
            async def process_and_send_video():
                while True:
                    video_data = await video_queue.get()

                    # Extract video bytes and mode from queue item
                    video_bytes = video_data.get("data")
                    video_mode = video_data.get("mode", "webcam")

                    logger.info(f"Processing video frame from {video_mode}")

                    # Send the video frame to Gemini through ADK
                    live_request_queue.send_realtime(
                        types.Blob(
                            data=video_bytes,
                            mime_type="image/jpeg",
                        )
                    )

                    video_queue.task_done()

            # Task to receive and process responses from ADK
            async def receive_and_process_responses():
                # Track user and model outputs between turn completion events
                input_texts = []
                output_texts = []
                current_session_id = None

                # Flag to track if we've seen an interruption in the current turn
                interrupted = False

                # Process responses from the agent
                async for event in runner.run_live(
                    session=session,
                    live_request_queue=live_request_queue,
                    run_config=run_config,
                ):
                    # Check for turn completion or interruption using string matching
                    # This is a fallback approach until a proper API exists
                    event_str = str(event)

                    # If there's a session resumption update, store the session ID
                    if hasattr(event, 'session_resumption_update') and event.session_resumption_update:
                        update = event.session_resumption_update
                        if update.resumable and update.new_handle:
                            current_session_id = update.new_handle
                            logger.info(f"New SESSION: {current_session_id}")
                            # Send session ID to client
                            session_id_msg = json.dumps({
                                "type": "session_id", 
                                "data": current_session_id
                            })
                            await websocket.send(session_id_msg)

                    # Handle content
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            # Process audio content
                            if hasattr(part, "inline_data") and part.inline_data:
                                b64_audio = base64.b64encode(part.inline_data.data).decode("utf-8")
                                await websocket.send(json.dumps({"type": "audio", "data": b64_audio}))

                            # Process text content
                            if hasattr(part, "text") and part.text:
                                # Check if this is user or model text based on content role
                                if hasattr(event.content, "role") and event.content.role == "user":
                                    # User text shouldn't be sent to the client
                                    input_texts.append(part.text)
                                else:
                                    # From the logs, we can see the duplicated text issue happens because
                                    # we get streaming chunks with "partial=True" followed by a final consolidated
                                    # response with "partial=None" containing the complete text

                                    # Check in the event string for the partial flag
                                    # Only process messages with "partial=True"
                                    if "partial=True" in event_str:
                                        await websocket.send(json.dumps({"type": "text", "data": part.text}))
                                        output_texts.append(part.text)
                                    # Skip messages with "partial=None" to avoid duplication

                    # Check for interruption
                    if event.interrupted and not interrupted:
                        logger.info("🤐 INTERRUPTION DETECTED")
                        await websocket.send(json.dumps({
                            "type": "interrupted",
                            "data": "Response interrupted by user input"
                        }))
                        interrupted = True

                    # Check for turn completion
                    if event.turn_complete:
                        # Only send turn_complete if there was no interruption
                        if not interrupted:
                            logger.info("✅ Gemini done talking")
                            await websocket.send(json.dumps({
                                "type": "turn_complete",
                                "session_id": current_session_id
                            }))

                        # Log collected transcriptions for debugging
                        if input_texts:
                            # Get unique texts to prevent duplication
                            unique_texts = list(dict.fromkeys(input_texts))
                            logger.info(f"Input transcription: {' '.join(unique_texts)}")

                        if output_texts:
                            # Get unique texts to prevent duplication
                            unique_texts = list(dict.fromkeys(output_texts))
                            logger.info(f"Output transcription: {' '.join(unique_texts)}")

                        # Reset for next turn
                        input_texts = []
                        output_texts = []
                        interrupted = False

            # Start all tasks
            tg.create_task(handle_websocket_messages(), name="MessageHandler")
            tg.create_task(process_and_send_audio(), name="AudioProcessor")
            tg.create_task(process_and_send_video(), name="VideoProcessor")
            tg.create_task(receive_and_process_responses(), name="ResponseHandler")


async def main():
    """Main function to start the server"""
    server = MultimodalADKServer()
    await server.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Exiting application via KeyboardInterrupt...")
    except Exception as e:
        logger.error(f"Unhandled exception in main: {e}")
        import traceback
        traceback.print_exc()