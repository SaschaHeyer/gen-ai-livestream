# Deploy to Vertex AI Agent Engine

This folder contains the scripts to deploy your Multi-Agent system to **Vertex AI Agent Engine**, a fully managed service for scaling AI agents.

## Prerequisites

1.  **Google Cloud Project**: Ensure you have a project set up (e.g., `sascha-playground-doit`).
2.  **Staging Bucket**: You need a Google Cloud Storage bucket for staging artifacts.
    *   Update `STAGING_BUCKET` in `deploy.py` with your bucket name (e.g., `gs://my-bucket`).
3.  **Permissions**: Ensure your user/service account has permissions to use Vertex AI and Cloud Storage.

## How to Deploy (CLI)

The easiest way to deploy is using the `adk deploy` command:

```bash
adk deploy agent_engine multi_agent \
        --display_name "Multi-Agent" \
        --project sascha-playground-doit \
        --region us-central1 \
        --env_file .env

```

## How to Deploy (Python Script)

Alternatively, you can run the provided Python script:

```bash
python3 workshop/agent_engine/deploy.py
```

*Note: Deployment can take several minutes (approx. 10-15 mins).*
