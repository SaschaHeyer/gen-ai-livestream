import asyncio
from google import genai
from google.genai import types

PROJECT_ID = "sascha-playground-doit"
LOCATION = "us-central1"
MODEL = "gemini-2.0-flash-live-preview-04-09"

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

config = {"response_modalities": ["AUDIO"],
          "output_audio_transcription": {}
}

async def main():
    async with client.aio.live.connect(model=MODEL, config=config) as session:
        message = "Hello? Gemini are you there?"

        await session.send_client_content(
            turns={"role": "user", "parts": [{"text": message}]}, turn_complete=True
        )

        async for response in session.receive():
            transcription = response.server_content.output_transcription
            if transcription and transcription.text:
                print(transcription.text, end="", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
