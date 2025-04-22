from google.adk.agents import Agent

import vertexai

PROJECT_ID = "sascha-playground-doit"
LOCATION = "us-central1"
STAGING_BUCKET = "gs://doit-llm"

vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
    staging_bucket=STAGING_BUCKET,
)

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

from vertexai import agent_engines


remote_app = agent_engines.create(
    agent_engine=root_agent,
    requirements=[
        "google-cloud-aiplatform[adk,agent_engines]"
    ]
)


#remote_app = agent_engines.AgentEngine(
#    "projects/234439745674/locations/us-central1/reasoningEngines/7069393573669502976"
#)

remote_session = remote_app.create_session(user_id="sascha")
print(remote_session)

for event in remote_app.stream_query(
    user_id="sascha",
    session_id=remote_session["id"],
    message="whats the weather in new york",
):
    print(event)
