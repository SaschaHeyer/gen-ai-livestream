import vertexai
from vertexai.preview import reasoning_engines
import base64

STAGING_BUCKET = "gs://doit-llm"
PROJECT_ID = "sascha-playground-doit"
LOCATION = "us-central1"

vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)

model = "gemini-2.0-pro-exp-02-05"
agent = reasoning_engines.LangchainAgent(
    model=model,
    system_instruction="""
    you behave like a pirate, every answer you response like a pirate
    """,
)

response = agent.query(
        input=f"Who are you?"
    )

print(response)


