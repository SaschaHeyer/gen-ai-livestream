import asyncio

from google import genai

PROJECT_ID = "backend-production-b8633498"
LOCATION = "us-central1"
# LOCATION = "global"


async def hello_world() -> None:
    model_id = "gemini-2.0-flash-live-preview-04-09"

    client = genai.Client(vertexai=True, location=LOCATION, project=PROJECT_ID)
    config = {"response_modalities": ["TEXT"]}

    async with client.aio.live.connect(model=model_id, config=config) as session:
        message = "Hello? Gemini, are you there?"
        print("> ", message, "\n")
        await session.send_client_content(turns={"role": "user", "parts": [{"text": message}]}, turn_complete=True)

        async for response in session.receive():
            print(response.text)


if __name__ == "__main__":

    asyncio.run(hello_world())
