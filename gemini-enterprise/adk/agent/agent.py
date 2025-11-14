# Conceptual Code: Coordinator using LLM Transfer
from google.adk.agents import LlmAgent

billing_agent = LlmAgent(
    name="Billing", model="gemini-2.0-flash", description="Handles billing inquiries.",
    instruction="Introduce yourself as Billii you are there to help with all billing related questions"
)

support_agent = LlmAgent(
    name="Support",
    model="gemini-2.0-flash",
    description="Handles technical support requests.",
    instruction="introduce yourself as techii. You are there to helpw ith any technical questions"
)

root_agent = LlmAgent(
    name="HelpDeskCoordinator",
    model="gemini-2.0-flash",
    instruction="Route user requests: Use Billing agent for payment issues, Support agent for technical problems.",
    description="Main help desk router.",
    # allow_transfer=True is often implicit with sub_agents in AutoFlow
    sub_agents=[billing_agent, support_agent],
)
# User asks "My payment failed" -> Coordinator's LLM should call transfer_to_agent(agent_name='Billing')
# User asks "I can't log in" -> Coordinator's LLM should call transfer_to_agent(agent_name='Support')

import vertexai
from vertexai import agent_engines

PROJECT_ID = "sascha-playground-doit"
LOCATION = "us-central1"  # For other options, see https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview#supported-regions
STAGING_BUCKET = "gs://doit-llm"


# Initialize the Vertex AI SDK
vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
    staging_bucket=STAGING_BUCKET,
)

app = agent_engines.AdkApp(
    agent=root_agent,
    enable_tracing=True,
    app_name="helpdesk-coordinator",
)

remote_app = agent_engines.create(
    agent_engine=app,
    requirements=[
        # Pin to the latest releases so Agent Engine surfaces like Traces stay enabled.
        "google-cloud-aiplatform[adk,agent_engines]==1.127.0",
        "google-adk==1.18.0",
    ]
)
