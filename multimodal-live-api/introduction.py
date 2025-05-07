
from google import genai

import asyncio
from google import genai
from google.genai.types import (
    Content,
    LiveConnectConfig,
    Part,
    PrebuiltVoiceConfig,
    SpeechConfig,
    VoiceConfig,
)
import numpy as np
import soundfile as sf

PROJECT_ID = "sascha-playground-doit"
LOCATION = "us-central1"
MODEL_ID = "gemini-2.0-flash-live-preview-04-09"
voice_name = "Aoede"

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

# For TEXT responses
text_config = LiveConnectConfig(
    response_modalities=["TEXT"]
)

# For AUDIO responses
audio_config = LiveConnectConfig(
    response_modalities=["AUDIO"],
    speech_config=SpeechConfig(
        voice_config=VoiceConfig(
            prebuilt_voice_config=PrebuiltVoiceConfig(voice_name=voice_name)
        )
    ),
)


async def main():
    text_input = "I am visiting Berlin in June what would you recommend to do there? " \
    "Plan the trip for me we are interested in museums and nightlife"
    print(f"> {text_input}\n")

    async with client.aio.live.connect(model=MODEL_ID, config=text_config) as session:
        await session.send_client_content(
            turns=Content(role="user", parts=[Part(text=text_input)])
        )


        audio_data = []

        async for message in session.receive():
            # Print streamed text
            if message.text:
                print(message.text, end="", flush=True)


            # Collect audio parts
            if message.server_content.model_turn and message.server_content.model_turn.parts:
                for part in message.server_content.model_turn.parts:
                    if part.inline_data:
                        audio_data.append(
                            np.frombuffer(part.inline_data.data, dtype=np.int16)
                        )

        if audio_data:
            audio = np.concatenate(audio_data)
            sf.write("output.wav", audio, 24000)
            print("🎧 Audio saved to output.wav")

if __name__ == "__main__":
    asyncio.run(main())
