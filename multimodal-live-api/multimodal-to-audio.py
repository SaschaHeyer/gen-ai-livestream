import asyncio
import traceback
import pyaudio
from collections import deque
import base64
import io
import argparse

import cv2  # For webcam
import PIL.Image  # For image processing
import mss  # For screen capture

from google import genai
from google.genai.types import (
    LiveConnectConfig,
    SpeechConfig,
    VoiceConfig,
    PrebuiltVoiceConfig,
)

# Polyfill for older Python versions if necessary
#if sys.version_info < (3, 11, 0):
    #try:
        #import taskgroup
        #import exceptiongroup
        #asyncio.TaskGroup = taskgroup.TaskGroup
        #asyncio.ExceptionGroup = exceptiongroup.ExceptionGroup
        #print("Applied taskgroup and exceptiongroup polyfills for Python < 3.11")
    #except ImportError:
        #print("Warning: Python < 3.11 detected and taskgroup/exceptiongroup polyfills not found. TaskGroup may not work.")


# --- Configuration ---
# Default values, can be overridden by CLI args
DEFAULT_PROJECT_ID = "sascha-playground-doit"
DEFAULT_LOCATION = "us-central1"
DEFAULT_MODEL = "gemini-2.0-flash-live-preview-04-09"

# Audio Configuration
AUDIO_FORMAT = pyaudio.paInt16
AUDIO_CHANNELS = 1
AUDIO_RECEIVE_SAMPLE_RATE = 24000
AUDIO_SEND_SAMPLE_RATE = 16000
AUDIO_CHUNK_SIZE = 512

FORMAT = pyaudio.paInt16
RECEIVE_SAMPLE_RATE = 24000
SEND_SAMPLE_RATE = 16000
CHUNK_SIZE = 512
CHANNELS = 1

# Video Configuration
VIDEO_FRAME_RATE_DELAY = 1.0
DEFAULT_VIDEO_MODE = "camera"

# --- Global Variables for Client Management ---
# These will store the actual values used by the current CLIENT_INSTANCE
# and the configuration for the current run.
CLIENT_INSTANCE = None
CURRENT_CLIENT_PROJECT_ID = None
CURRENT_CLIENT_LOCATION = None

# These will hold the active configuration for the current run, updated by CLI args.
ACTIVE_PROJECT_ID = DEFAULT_PROJECT_ID
ACTIVE_LOCATION = DEFAULT_LOCATION
ACTIVE_MODEL = DEFAULT_MODEL

# CONFIG for LiveConnect, can reference ACTIVE_MODEL if model name is part of it,
# but for LiveConnectConfig, model is passed to connect() method.
LIVE_CONNECT_CONFIG = LiveConnectConfig(
    response_modalities=["AUDIO"],
    speech_config=SpeechConfig(
        voice_config=VoiceConfig(
            prebuilt_voice_config=PrebuiltVoiceConfig(voice_name="Puck")
        )
    ),
    system_instruction="you are a super friendly, sometime a bit to friendly assistant.",
)

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

# --- Video Helper Functions ---
async def _get_frame_data(cap):
    ret, frame = await asyncio.to_thread(cap.read)
    if not ret: print("⚠️ Failed to capture frame from webcam."); return None
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = PIL.Image.fromarray(frame_rgb)
    img.thumbnail([512, 512])
    image_io = io.BytesIO()
    img.save(image_io, format="jpeg", quality=70)
    image_io.seek(0); image_bytes = image_io.read()
    return {"mime_type": "image/jpeg", "data": base64.b64encode(image_bytes).decode()}

async def _get_screen_data(sct, monitor):
    loop = asyncio.get_event_loop() # mss might need loop for run_in_executor if it's not thread-safe itself
    try:
        sct_img = await loop.run_in_executor(None, sct.grab, monitor)
        if not sct_img: print("⚠️ Failed to capture screen."); return None
        img = PIL.Image.frombytes('RGB', (sct_img.width, sct_img.height), sct_img.rgb)
        img.thumbnail([768, 768])
        image_io = io.BytesIO()
        img.save(image_io, format="jpeg", quality=70)
        image_io.seek(0); image_bytes = image_io.read()
        return {"mime_type": "image/jpeg", "data": base64.b64encode(image_bytes).decode()}
    except Exception as e: print(f"Error capturing screen: {e}"); return None

# --- Main Conversation Loop ---
async def main_conversation_loop(video_mode: str, cli_project_id_arg: str, cli_location_arg: str, cli_model_arg: str):
    global CLIENT_INSTANCE, ACTIVE_PROJECT_ID, ACTIVE_LOCATION, ACTIVE_MODEL, CURRENT_CLIENT_PROJECT_ID, CURRENT_CLIENT_LOCATION, LIVE_CONNECT_CONFIG

    # Update active configuration from CLI args if provided, otherwise use defaults
    project_to_use = cli_project_id_arg if cli_project_id_arg else DEFAULT_PROJECT_ID
    location_to_use = cli_location_arg if cli_location_arg else DEFAULT_LOCATION
    model_to_use = cli_model_arg if cli_model_arg else DEFAULT_MODEL

    # Update global active configuration
    ACTIVE_PROJECT_ID = project_to_use
    ACTIVE_LOCATION = location_to_use
    ACTIVE_MODEL = model_to_use

    needs_reinit = False
    if CLIENT_INSTANCE is None:
        needs_reinit = True
        print("Client is None, needs initialization.")
    elif project_to_use != CURRENT_CLIENT_PROJECT_ID:
        needs_reinit = True
        print(f"Project ID changed ('{CURRENT_CLIENT_PROJECT_ID}' -> '{project_to_use}'), re-initializing client.")
    elif location_to_use != CURRENT_CLIENT_LOCATION:
        needs_reinit = True
        print(f"Location changed ('{CURRENT_CLIENT_LOCATION}' -> '{location_to_use}'), re-initializing client.")

    if needs_reinit:
        print(f"Attempting to initialize/re-initialize Google GenAI Client with Project: {ACTIVE_PROJECT_ID}, Location: {ACTIVE_LOCATION}")
        try:
            CLIENT_INSTANCE = genai.Client(vertexai=True, project=ACTIVE_PROJECT_ID, location=ACTIVE_LOCATION)
            CURRENT_CLIENT_PROJECT_ID = ACTIVE_PROJECT_ID # Store what the client was initialized with
            CURRENT_CLIENT_LOCATION = ACTIVE_LOCATION
            print("Client successfully initialized/re-initialized.")
        except Exception as e:
            print(f"FATAL: Error initializing/re-initializing Google GenAI Client: {e}. Exiting."); traceback.print_exc(); return

    if CLIENT_INSTANCE is None: print("FATAL: Google GenAI Client is not available. Exiting."); return
    print(f"Starting main loop with Model: {ACTIVE_MODEL}, Video: {video_mode}")

    audio_manager = AudioManager(
        input_sample_rate=SEND_SAMPLE_RATE, output_sample_rate=RECEIVE_SAMPLE_RATE
    )

    await audio_manager.initialize()

    audio_send_queue = asyncio.Queue(maxsize=100)
    video_send_queue = asyncio.Queue(maxsize=10)
    stop_event = asyncio.Event()
    cap, sct = None, None # Initialize for finally block

    try:
        # Use CLIENT_INSTANCE here
        async with CLIENT_INSTANCE.aio.live.connect(model=ACTIVE_MODEL, config=LIVE_CONNECT_CONFIG) as session, \
                   asyncio.TaskGroup() as tg:

            print("DEBUG: Entered TaskGroup and LiveConnect session.")
            video_capture_active_flag = False

            async def listen_for_audio():
                print("🎤 AudioListener: Listening...")
                while not stop_event.is_set():
                    try:
                        data = await asyncio.to_thread(audio_manager.input_stream.read, AUDIO_CHUNK_SIZE, exception_on_overflow=False)
                        await audio_send_queue.put(data)
                    except IOError as e:
                        if hasattr(e, 'errno') and e.errno == pyaudio.paInputOverflowed: print("🎤 AudioListener: Input overflowed."); continue
                        print(f"🎤 AudioListener: IOError: {e}."); await asyncio.sleep(0.5)
                    except Exception as e:
                        print(f"🎤 AudioListener: Error: {e}")
                        if audio_manager.input_stream and not audio_manager.input_stream.is_active():
                            print("🎤 AudioListener: Input stream died. Re-init AudioManager."); await audio_manager.initialize()
                        await asyncio.sleep(0.1)
                print("🎤 AudioListener: Stop event set. Exiting.")

            async def process_and_send_audio():
                print("🔊 AudioSender: Started.")
                while not stop_event.is_set() or not audio_send_queue.empty():
                    try:
                        data = await asyncio.wait_for(audio_send_queue.get(), timeout=0.5)
                        await session.send_realtime_input(media={"data": data, "mime_type": f"audio/pcm;rate={AUDIO_SEND_SAMPLE_RATE}"})
                        audio_send_queue.task_done()
                    except asyncio.TimeoutError:
                        if stop_event.is_set() and audio_send_queue.empty(): break; continue
                    except Exception as e: print(f"🔊 AudioSender: Error: {e}"); await asyncio.sleep(0.1)
                print("🔊 AudioSender: Stop event. Exiting.")

            if video_mode == "camera":
                print("📹 VideoCapture: Initializing webcam...")
                cap = await asyncio.to_thread(cv2.VideoCapture, 0)
                if not cap.isOpened(): print("❌ VideoCapture: Cannot open webcam.")
                else: video_capture_active_flag = True; print(f"📹 VideoCapture: Webcam started.")
                async def stream_video_frames_inner():
                    while video_capture_active_flag and not stop_event.is_set():
                        frame_media = await _get_frame_data(cap)
                        if frame_media: await video_send_queue.put(frame_media)
                        else: print("📹 VideoCapture: No frame_media from webcam."); # Consider stopping if persistent
                        await asyncio.sleep(VIDEO_FRAME_RATE_DELAY)
                    if cap and cap.isOpened(): await asyncio.to_thread(cap.release)
                    print("📹 VideoCapture: Webcam task ended.")
                if video_capture_active_flag: tg.create_task(stream_video_frames_inner(), name="WebcamStreamer")

            elif video_mode == "screen":
                print("🖥️ ScreenCapture: Initializing...")
                try:
                    sct = await asyncio.to_thread(mss.mss)
                    monitor = await asyncio.to_thread(lambda: sct.monitors[1])
                    video_capture_active_flag = True; print(f"🖥️ ScreenCapture: Started for monitor {monitor}.")
                    async def stream_screen_capture_inner():
                        while video_capture_active_flag and not stop_event.is_set():
                            screen_media = await _get_screen_data(sct, monitor)
                            if screen_media: await video_send_queue.put(screen_media)
                            else: print("🖥️ ScreenCapture: No screen_media."); # Consider stopping
                            await asyncio.sleep(VIDEO_FRAME_RATE_DELAY)
                        print("🖥️ ScreenCapture: Screen task ended.")
                    if video_capture_active_flag: tg.create_task(stream_screen_capture_inner(), name="ScreenStreamer")
                except Exception as e: print(f"❌ ScreenCapture: Failed: {e}.")

            if video_capture_active_flag:
                async def process_and_send_video():
                    print(f"🖼️ VideoSender: Started (mode: {video_mode}).")
                    while not stop_event.is_set() or not video_send_queue.empty():
                        try:
                            video_data = await asyncio.wait_for(video_send_queue.get(), timeout=0.5)
                            await session.send_realtime_input(media=video_data)
                            video_send_queue.task_done()
                        except asyncio.TimeoutError:
                            if stop_event.is_set() and video_send_queue.empty(): break; continue
                        except Exception as e: print(f"🖼️ VideoSender: Error: {e}"); await asyncio.sleep(0.1)
                    print("🖼️ VideoSender: Stop event. Exiting.")
                tg.create_task(process_and_send_video(), name="VideoSender")

            async def receive_and_play():
                print("👂 Receiver: Waiting for Gemini's response...")
                while not stop_event.is_set():
                    try:
                        async for response in session.receive():
                            if stop_event.is_set(): break
                            print(f"👂 Receiver: Got response. Server content type: {type(response.server_content).__name__ if response.server_content else 'None'}")
                            server_content = response.server_content
                            if hasattr(server_content, "interrupted") and server_content.interrupted:
                                print("🤐 Receiver: INTERRUPTION from server."); audio_manager.interrupt()
                            if server_content and server_content.model_turn:
                                for part in server_content.model_turn.parts:
                                    if part.inline_data:
                                        print(f"👂 Receiver: Calling audio_manager.add_audio (chunk size {len(part.inline_data.data)})")
                                        audio_manager.add_audio(part.inline_data.data)
                                    if part.text: print(f"ℹ️ Receiver: Gemini (text): {part.text}")
                            if server_content and server_content.turn_complete: print("✅ Receiver: Gemini turn complete.")
                    except asyncio.CancelledError: print("👂 Receiver: Task cancelled."); break
                    except Exception as e:
                        print(f"👂 Receiver: Error: {e}"); traceback.print_exc()
                        if "LiveSession._receive_stream_broken" in str(e) or " RST_STREAM " in str(e): # Check for stream errors
                            print("👂 Receiver: Session stream broken. Setting stop event."); stop_event.set(); break
                        await asyncio.sleep(0.1)
                print("👂 Receiver: Stop event. Exiting.")

            tg.create_task(listen_for_audio(), name="AudioListener")
            tg.create_task(process_and_send_audio(), name="AudioSender")
            tg.create_task(receive_and_play(), name="GeminiReceiver")
            print(f"🚀 All tasks started. Video mode: {video_mode}. Press Ctrl+C to exit.")
            await stop_event.wait()

    except KeyboardInterrupt: print("\n👋 KeyboardInterrupt. Shutting down...")
    except asyncio.CancelledError: print("Main conversation loop cancelled.")
    except Exception as e: print(f"💥 Unhandled exception in main_conversation_loop: {e}"); traceback.print_exc()
    finally:
        print("Cleaning up resources...")
        stop_event.set()
        if 'video_capture_active_flag' in locals(): video_capture_active_flag = False # Signal video loops
        print("Waiting for tasks to finish (1s)..."); await asyncio.sleep(1.0)
        if audio_manager: audio_manager.close_streams()
        if video_mode == "camera" and cap and cap.isOpened(): print("Releasing webcam."); await asyncio.to_thread(cap.release)
        if video_mode == "screen" and sct and hasattr(sct, 'close'): print("Closing screen capture."); await asyncio.to_thread(sct.close)
        print("Application cleanup complete. Exiting.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bidirectional audio/video streaming with Google Gemini Live API.")
    parser.add_argument("--mode", type=str, default=DEFAULT_VIDEO_MODE, help="Video streaming mode.", choices=["camera", "screen", "none"])
    parser.add_argument("--project_id", type=str, default=None, help=f"Google Cloud Project ID (default: {DEFAULT_PROJECT_ID}).") # Default to None to use hardcoded if not provided
    parser.add_argument("--location", type=str, default=None, help=f"Google Cloud Location (default: {DEFAULT_LOCATION}).")
    parser.add_argument("--model", type=str, default=None, help=f"Gemini model name (default: {DEFAULT_MODEL}).")
    args = parser.parse_args()

    print(f"Starting Live API client with CLI args (or defaults):")
    print(f"  Project ID to use: {args.project_id if args.project_id else DEFAULT_PROJECT_ID}")
    print(f"  Location to use: {args.location if args.location else DEFAULT_LOCATION}")
    print(f"  Model to use: {args.model if args.model else DEFAULT_MODEL}")
    print(f"  Video Mode: {args.mode}")

    try:
        asyncio.run(main_conversation_loop( # Use asyncio.run
            video_mode=args.mode,
            cli_project_id_arg=args.project_id,
            cli_location_arg=args.location,
            cli_model_arg=args.model
        ))
    except KeyboardInterrupt: print("Application terminated by user (main __name__ block).")
    except Exception as e: print(f"Unhandled exception in __main__: {e}"); traceback.print_exc()
    finally:
        print("Main execution finished.")
