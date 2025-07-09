from google.adk.agents import Agent

root_agent = Agent(
    name="homer_simpson_agent",
    model="gemini-2.0-flash-exp",
    description=(
        "Agent to answer only questions related to the simpsons"
    ),
    instruction=(
        """you are a agent that only answers questions related to the simpsons.
        you also sound and act like homer simpson"""
    ),
)




import vertexai

PROJECT_ID = "sascha-playground-doit"
LOCATION = "us-central1"
STAGING_BUCKET = "gs://doit-llm"

vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
    staging_bucket=STAGING_BUCKET,
)

from vertexai import agent_engines

remote_app = agent_engines.create(
    agent_engine=root_agent,
    requirements=[
        "google-cloud-aiplatform[adk,agent_engines]"
    ]
)
