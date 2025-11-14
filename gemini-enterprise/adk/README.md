# Gemini Enterprise ADK Workshop

This directory contains the assets needed to showcase how a Vertex AI Agent Development Kit (ADK) agent can be deployed to Vertex AI Agent Engine and then registered with Gemini Enterprise. The workflow mirrors the official documentation at https://docs.cloud.google.com/gemini/enterprise/docs/register-and-manage-an-adk-agent and should serve as a repeatable reference for the workshop.

> **Preview notice (November 2025):** Registering ADK agents with Gemini Enterprise is still a Pre-GA/Preview feature. Expect occasional breaking changes and limited UI support. Always review the latest release notes before demos.

## Contents

| Path | Purpose |
| --- | --- |
| `agent/agent.py` | Sample coordinator ADK agent that routes between “Billing” and “Support” sub-agents and deploys via `vertexai.agent_engines`. |
| `register/register_agent.py` | Python CLI for calling the Discovery Engine v1alpha API to register an ADK deployment with a Gemini Enterprise app. |
| `register/register.sh` | Fixed-argument wrapper around `register_agent.py` so you can rerun the same registration command later without hunting for flags. |

## Prerequisites

1. **Google Cloud project setup**
   - Discovery Engine API enabled.
   - Gemini Enterprise app already created.
   - `gcloud` authenticated (`gcloud auth application-default login`).
2. **Vertex AI Agent Engine deployment**
   - Use `agent/agent.py` (or your own ADK build) to create a reasoning engine.
   - Ensure the `requirements` list includes `google-cloud-aiplatform[adk,agent_engines]==1.127.0` and `google-adk==1.18.0` (or later) so the Agent Engine dashboard and traces features remain available.
3. **Python ≥ 3.9** with the `google-auth` stack available (install via `pip install google-auth google-auth-httplib2 google-auth-oauthlib` if needed).

## Deploying the sample ADK agent

```bash
cd agent
python agent.py
```

This script:

1. Initializes Vertex AI (`vertexai.init`).
2. Builds a coordinator agent with two sub-agents.
3. Calls `agent_engines.create(...)` to deploy and returns the reasoning engine ID (save it for registration).

## Registering the agent with Gemini Enterprise

There are two options:

### 1. One-off custom command

```bash
python register/register_agent.py \
  --project-id "my-project" \
  --app-id "my-gemini-app" \
  --display-name "Help Desk Coordinator" \
  --description "Routes billing vs. support inquiries." \
  --reasoning-engine-location "us-central1" \
  --adk-deployment-id "1234567890" \
  --location "global" \
  --endpoint "global" \
  --icon-file "/path/to/icon.png"
```

Use `--dry-run` to inspect the payload before sending, `--authorization-id` for OAuth tool authorizations, or `--icon-uri` if your image is already hosted.

### 2. Repeatable wrapper

`register/register.sh` hardcodes the workshop defaults:

```bash
cd register
chmod +x register.sh   # once
./register.sh
```

Append extra flags if you need to override something temporarily (for example, `./register.sh --dry-run`).
