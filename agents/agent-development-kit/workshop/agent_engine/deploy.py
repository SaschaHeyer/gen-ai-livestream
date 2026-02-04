
import os
import vertexai
from vertexai.preview import agent_engines
from agent import app  # Import the app directly

# --- Configuration ---
PROJECT_ID = "sascha-playground-doit"
LOCATION = "us-central1"
STAGING_BUCKET = "gs://sascha-playground-doit-staging"

# Initialize Vertex AI
vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
    staging_bucket=STAGING_BUCKET,
)

print(f"Deploying agent to Agent Engine in project {PROJECT_ID}...")

# Deploy the agent
remote_app = agent_engines.create(
    agent_engine=app, # Deploy the pre-defined app
    requirements=[
        "google-cloud-aiplatform[adk,agent_engines]==1.135.0",
        "google-adk" 
    ]
)

print("Deployment complete!")
print(f"Resource Name: {remote_app.resource_name}")
