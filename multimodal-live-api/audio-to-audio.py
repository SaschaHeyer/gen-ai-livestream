import asyncio
import traceback
import pyaudio
from collections import deque

from google import genai
from google.genai import types

PROJECT_ID = "sascha-playground-doit"
LOCATION = "us-central1"
MODEL = "gemini-2.0-flash-live-preview-04-09"

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

FORMAT = pyaudio.paInt16
RECEIVE_SAMPLE_RATE = 24000
SEND_SAMPLE_RATE = 16000
CHUNK_SIZE = 512
CHANNELS = 1

from google.genai.types import (
    LiveConnectConfig,
    SpeechConfig,
    VoiceConfig,
    PrebuiltVoiceConfig,
)

CONFIG = LiveConnectConfig(
    response_modalities=["AUDIO"],
    output_audio_transcription={},
    input_audio_transcription={},
    #session_resumption=types.SessionResumptionConfig(
                # The handle of the session to resume is passed here,
                # or else None to start a new session.
                #handle="93f6ae1d-2420-40e9-828c-776cf553b7a6"
            #),
    speech_config=SpeechConfig(
        voice_config=VoiceConfig(
            prebuilt_voice_config=PrebuiltVoiceConfig(voice_name="Puck")
        )
    ),
    system_instruction="you are a super friendly, sometime a bit to friendly",
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


async def audio_loop():
    audio_manager = AudioManager(
        input_sample_rate=SEND_SAMPLE_RATE, output_sample_rate=RECEIVE_SAMPLE_RATE
    )

    await audio_manager.initialize()

    async with (
        client.aio.live.connect(model=MODEL, config=CONFIG) as session,
        asyncio.TaskGroup() as tg,
    ):

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

                # Always send the audio data to Gemini
                await session.send_realtime_input(
                    media={
                        "data": data,
                        "mime_type": f"audio/pcm;rate={SEND_SAMPLE_RATE}",
                    }
                )

                audio_queue.task_done()

        async def receive_and_play():
            while True:

                input_transcriptions = []
                output_transcriptions = []

                async for response in session.receive():

                    # retrieve continously resumable session ID
                    if response.session_resumption_update:
                        update = response.session_resumption_update
                        if update.resumable and update.new_handle:
                            # The handle should be retained and linked to the session.
                            print(f"new SESSION: {update.new_handle}")

                    # Check if the connection will be soon terminated
                    if response.go_away is not None:
                        print(response.go_away.time_left)

                    server_content = response.server_content

                    if (
                        hasattr(server_content, "interrupted")
                        and server_content.interrupted
                    ):
                        print(f"🤐 INTERRUPTION DETECTED")
                        audio_manager.interrupt()

                    if server_content and server_content.model_turn:
                        for part in server_content.model_turn.parts:
                            if part.inline_data:
                                audio_manager.add_audio(part.inline_data.data)

                    if server_content and server_content.turn_complete:
                        print("✅ Gemini done talking")

                    output_transcription = response.server_content.output_transcription
                    if output_transcription and output_transcription.text:
                        output_transcriptions.append(output_transcription.text)

                    input_transcription = response.server_content.input_transcription
                    if input_transcription and input_transcription.text:
                        input_transcriptions.append(input_transcription.text)

                print(f"Output transcription: {''.join(output_transcriptions)}")
                print(f"Input transcription: {''.join(input_transcriptions)}")

        # Start all tasks with proper task creation
        tg.create_task(listen_for_audio())
        tg.create_task(process_and_send_audio())
        tg.create_task(receive_and_play())


if __name__ == "__main__":
    try:
        asyncio.run(audio_loop(), debug=True)
    except KeyboardInterrupt:
        print("Exiting application via KeyboardInterrupt...")
    except Exception as e:
        print(f"Unhandled exception in main: {e}")
        traceback.print_exc()
