"""
Video Ingredient Detection WebSocket Server using LiveAPI
---------------------------------------------------------
This server uses the Gemini LiveAPI to handle a continuous stream of
webcam frames from a browser. It establishes a persistent session with the
model, feeding it frames until an ingredient list is detected on food
packaging.

Expected WebSocket message types (JSON):
- {"type": "frame", "data": "<BASE64 JPEG>"}

Server → Client message types (JSON)
- {"type": "status", "data": "scanning"}
- {"type": "found"}
- {"type": "ingredients", "data": "Sugar, Wheat flour, …"}
"""

from __future__ import annotations

import asyncio
import base64
import json

# Google Gemini SDK
from google import genai
from google.genai.types import LiveConnectConfig

# Shared utilities / constants
from common import (
    BaseWebSocketServer,
    logger,
    PROJECT_ID,
    LOCATION,
    MODEL,
    SYSTEM_INSTRUCTION,
)

# Initialize Google client
# A single client instance is reused for all connections.
client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

# LiveAPI Configuration for Video Input and Text Output
config = LiveConnectConfig(
    # Specify that we want text responses from the model.
    response_modalities=["TEXT"],
    # Specify that we will be sending video input.
    # input_video_config={},
    # Provide the model with instructions on how to behave.
    system_instruction=SYSTEM_INSTRUCTION,
)


class LiveVideoWebSocketServer(BaseWebSocketServer):
    """WebSocket server implementation using Gemini LiveAPI for video."""

    async def process_audio(self, websocket, client_id):
        """
        Processes incoming video frames from the client via a WebSocket
        connection using the Gemini LiveAPI.

        Note: The method is named process_audio in the base class, but here
        it is adapted to handle video frames.
        """
        self.active_clients[client_id] = websocket
        ingredients_found = False
        print("We're here")
        # Connect to Gemini using the LiveAPI.
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            async with asyncio.TaskGroup() as tg:
                frame_queue = asyncio.Queue()

                # Task 1: Handle incoming WebSocket messages from the browser.
                async def handle_websocket_messages():
                    async for message in websocket:
                        try:
                            data = json.loads(message)

                            if data.get("type") == "frame":
                                # Decode the base64 image and put it in the queue.
                                img_bytes = base64.b64decode(data.get("data", ""))
                                await frame_queue.put(img_bytes)
                        except json.JSONDecodeError:
                            logger.error("Invalid JSON message received")
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")

                # Task 2: Send video frames from the queue to the Gemini session.
                async def send_frames_to_gemini():
                    while True:
                        frame_bytes = await frame_queue.get()
                        print(f"Sending message to gemini")
                        # Send the raw image bytes to the LiveAPI session.
                        await session.send_realtime_input(
                            media={"data": frame_bytes, "mime_type": "image/jpeg"}
                        )
                        frame_queue.task_done()

                # Task 3: Receive and process text responses from Gemini.
                async def receive_responses_from_gemini():
                    nonlocal ingredients_found
                    await websocket.send(
                        json.dumps({"type": "status", "data": "scanning"})
                    )

                    async for response in session.receive():
                        server_content = response.server_content
                        print(f"Got message from gemini {server_content}")
                        if server_content and server_content.model_turn:
                            for part in server_content.model_turn.parts:
                                if part.text:
                                    logger.info(f"Gemini response: '{part.text.strip()}'")
                                    # Check if the model found ingredients.
                                    if "NO_INGREDIENTS_FOUND" not in part.text.upper():
                                        if not ingredients_found:
                                            ingredients_found = True
                                            # Notify UI that ingredients were found.
                                            await websocket.send(json.dumps({"type": "found"}))
                                            # Send the extracted ingredients list.
                                            await websocket.send(json.dumps({
                                                "type": "ingredients",
                                                "data": part.text.strip(),
                                            }))
                                    else:
                                        # Inform UI that we're still looking.
                                        await websocket.send(json.dumps({
                                            "type": "status",
                                            "data": "scanning"
                                        }))


                # Start all concurrent tasks.
                tg.create_task(handle_websocket_messages())
                tg.create_task(send_frames_to_gemini())
                tg.create_task(receive_responses_from_gemini())


async def main():
    """Main function to start the server."""
    server = LiveVideoWebSocketServer()
    await server.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Exiting application via KeyboardInterrupt...")