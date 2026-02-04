import vertexai
import asyncio

client = vertexai.Client(  # For service interactions via client.agent_engines
    project="sascha-playground-doit",
    location="us-central1",
)

adk_app = client.agent_engines.get(name="projects/234439745674/locations/us-central1/reasoningEngines/3156182212391469056")

#print(adk_app)

async def main():
    async for event in adk_app.async_stream_query(
        user_id="USER_ID",
        #session_id="SESSION_ID",  # Optional
        message="I want to fly from Berlin to Stockholm?",
    ):
        if "content" in event and event["content"].get("parts"):
            text = event["content"]["parts"][0].get("text")
            if text:
                print(text)

if __name__ == "__main__":
    asyncio.run(main())
