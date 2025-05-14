import asyncio
import random
import pyaudio
from collections import deque
import os
from dotenv import load_dotenv

from google.adk.agents import Agent, LiveRequestQueue
from google.adk.runners import Runner
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.sessions.session import Session
from google.genai import types
from google import genai

# For Vertex AI setup
import vertexai
from vertexai.generative_models import GenerationConfig

# Load environment variables from .env file
load_dotenv()

# Audio configuration
FORMAT = pyaudio.paInt16
RECEIVE_SAMPLE_RATE = 24000
SEND_SAMPLE_RATE = 16000
CHUNK_SIZE = 512
CHANNELS = 1

# Project configuration
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "sascha-playground-doit")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL = "gemini-2.0-flash-live-preview-04-09"
VOICE_NAME = "Aoede"  # Changed from "Puck" to "Aoede"

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location=LOCATION)
genai.Client(project=PROJECT_ID, location=LOCATION, vertexai=True)
print(f"Initialized Vertex AI with project: {PROJECT_ID}, location: {LOCATION}")


# Mock function for get_order_status
def get_order_status(order_id):
    """Mock order status API that returns randomized status for an order ID."""
    # Define possible order statuses and shipment methods
    statuses = ["processing", "shipped", "delivered"]
    shipment_methods = ["standard", "express", "next day", "international"]

    # Generate random data based on the order ID to ensure consistency for the same ID
    # Using the sum of ASCII values of the order ID as a seed
    seed = sum(ord(c) for c in str(order_id))
    random.seed(seed)

    # Generate order data
    status = random.choice(statuses)
    shipment = random.choice(shipment_methods)

    # Generate dates based on status
    order_date = "2024-05-" + str(random.randint(12, 28)).zfill(2)

    estimated_delivery = None
    shipped_date = None
    delivered_date = None

    if status == "processing":
        estimated_delivery = "2024-06-" + str(random.randint(1, 15)).zfill(2)
    elif status == "shipped":
        shipped_date = "2024-05-" + str(random.randint(1, 28)).zfill(2)
        estimated_delivery = "2024-06-" + str(random.randint(1, 15)).zfill(2)
    elif status == "delivered":
        shipped_date = "2024-05-" + str(random.randint(1, 20)).zfill(2)
        delivered_date = "2024-05-" + str(random.randint(21, 28)).zfill(2)

    # Reset random seed to ensure other functions aren't affected
    random.seed()

    result = {
        "order_id": order_id,
        "status": status,
        "order_date": order_date,
        "shipment_method": shipment,
        "estimated_delivery": estimated_delivery,
    }

    if shipped_date:
        result["shipped_date"] = shipped_date

    if delivered_date:
        result["delivered_date"] = delivered_date

    print(f"Order status for {order_id}: {status}")

    return result


class AudioManager:
    def __init__(self, input_sample_rate=16000, output_sample_rate=24000):
        self.pya = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None
        self.input_sample_rate = input_sample_rate
        self.output_sample_rate = output_sample_rate
        self.audio_queue = deque()
        self.is_playing = False
        self.playback_task = None

    async def initialize(self):
        mic_info = self.pya.get_default_input_device_info()
        print(f"microphone used: {mic_info}")

        self.input_stream = await asyncio.to_thread(
            self.pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=self.input_sample_rate,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )

        self.output_stream = await asyncio.to_thread(
            self.pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=self.output_sample_rate,
            output=True,
        )

    def add_audio(self, audio_data):
        """Add audio data to the playback queue"""
        self.audio_queue.append(audio_data)

        if self.playback_task is None or self.playback_task.done():
            self.playback_task = asyncio.create_task(self.play_audio())

    async def play_audio(self):
        """Play all queued audio data"""
        print("🗣️ Gemini talking")
        while self.audio_queue:
            try:
                audio_data = self.audio_queue.popleft()
                await asyncio.to_thread(self.output_stream.write, audio_data)
            except Exception as e:
                print(f"Error playing audio: {e}")

        self.is_playing = False

    def interrupt(self):
        """Handle interruption by stopping playback and clearing queue"""
        self.audio_queue.clear()
        self.is_playing = False

        # Important: Start a clean state for next response
        if self.playback_task and not self.playback_task.done():
            self.playback_task.cancel()


# Define a function tool for get_order_status
def order_status_tool(order_id: str):
    """Get the current status and details of an order.

    Args:
        order_id: The order ID to look up.

    Returns:
        Dictionary containing order status details
    """
    return get_order_status(order_id)


async def audio_loop():
    # Initialize audio manager
    audio_manager = AudioManager(
        input_sample_rate=SEND_SAMPLE_RATE, output_sample_rate=RECEIVE_SAMPLE_RATE
    )
    await audio_manager.initialize()

    # Create ADK agent with tools
    agent = Agent(
        name="customer_service_agent",
        model=MODEL,
        instruction="You are a helpful customer service assistant for an online store. You can help customers check the status of their orders. When asked about an order, you should ask for the order ID and then use the order_status_tool to retrieve the information. Be courteous, professional, and provide all relevant details about shipping, delivery dates, and current status.",
        tools=[order_status_tool],
    )

    # Create session service and session
    session_service = InMemorySessionService()
    session = session_service.create_session(
        app_name="audio_assistant",
        user_id="test_user",
        session_id="audio_session"
    )

    # Create runner
    runner = Runner(
        app_name="audio_assistant",
        agent=agent,
        session_service=session_service,
    )

    # Create live request queue
    live_request_queue = LiveRequestQueue()

    # Create run config with audio settings
    run_config = RunConfig(
        streaming_mode=StreamingMode.BIDI,
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE_NAME)
            )
        ),
        response_modalities=["AUDIO"],
        output_audio_transcription=types.AudioTranscriptionConfig(),
        input_audio_transcription=types.AudioTranscriptionConfig(),
    )

    # Queue for user audio chunks to control flow
    audio_queue = asyncio.Queue()

    async def listen_for_audio():
        """Just captures audio and puts it in the queue"""
        while True:
            data = await asyncio.to_thread(
                audio_manager.input_stream.read,
                CHUNK_SIZE,
                exception_on_overflow=False,
            )
            await audio_queue.put(data)

    async def process_and_send_audio():
        """Processes audio from queue and sends to Gemini"""
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

    async def receive_and_process_responses():
        input_transcriptions = []
        output_transcriptions = []
        LOG_FILE = "event_log.txt"
        import json
        from datetime import datetime
        with open(LOG_FILE, "a", encoding="utf-8") as log_file:
            # Process responses from the agent
            async for event in runner.run_live(
                session=session,
                live_request_queue=live_request_queue,
                run_config=run_config,
            ):

                log_entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "event": event.to_dict() if hasattr(event, "to_dict") else str(event)
                }
                log_file.write(json.dumps(log_entry) + "\n")
                log_file.flush()
                # Handle model response
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            # Play audio response
                            audio_manager.add_audio(part.inline_data.data)

                        # Check for transcriptions
                        if hasattr(part, 'text') and part.text:
                            print(f"Model response: {part.text}")
                            output_transcriptions.append(part.text)

                # Check for turn completion
                if event.actions.state_delta.get("turn_complete", False):
                    print("✅ Gemini done talking")

                # Check for interruption
                if event.actions.state_delta.get("interrupted", False):
                    print("🤐 INTERRUPTION DETECTED")
                    audio_manager.interrupt()

    # Run everything concurrently
    async with asyncio.TaskGroup() as tg:
        tg.create_task(listen_for_audio())
        tg.create_task(process_and_send_audio())
        tg.create_task(receive_and_process_responses())


if __name__ == "__main__":
    try:
        asyncio.run(audio_loop(), debug=True)
    except KeyboardInterrupt:
        print("Exiting application via KeyboardInterrupt...")
    except Exception as e:
        print(f"Unhandled exception in main: {e}")
        import traceback
        traceback.print_exc()
