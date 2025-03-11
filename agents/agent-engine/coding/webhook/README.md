# GitHub Webhook Server

This service processes GitHub webhooks to:
1. Analyze new issues with Vertex AI Reasoning Engine
2. Generate and store embeddings for code files in Firestore

## Environment Setup

This service uses environment variables for secrets management. Create a `.env` file with the following variables:

```
GITHUB_TOKEN=your_github_token
AGENT_ENGINE=projects/your_project_id/locations/your_location/reasoningEngines/your_engine_id
```

## Installation

```bash
pip install -r requirements.txt
```

## Running the Service

```bash
python webhook.py
```

The webhook server will run on port 8080 by default.

## Deployment

The included Dockerfile and cloudbuild.yaml can be used to deploy this service to Google Cloud Run.