# GitHub Agent & Webhook System

<div align="center">
  <img src="https://img.shields.io/badge/Language-Python-blue?style=flat-square&logo=python">
  <img src="https://img.shields.io/badge/AI-Google_Vertex_AI-green?style=flat-square&logo=google-cloud">
  <img src="https://img.shields.io/badge/Platform-GitHub-black?style=flat-square&logo=github">
</div>

## 🤖 Overview

This system combines an AI-powered agent with a webhook service to automatically analyze and resolve GitHub issues. Using Google's Vertex AI Reasoning Engines, it can:

- 📝 Understand issue requirements and bug reports
- 🔍 Search codebases for relevant code using two different approaches
- 🛠️ Implement solutions and create pull requests
- 🗣️ Provide detailed explanations in issue comments

## 🏗️ Architecture

```
┌─────────────┐           ┌──────────────┐           ┌──────────────┐
│  GitHub     │◄──Push───►│   Webhook    │◄─────────►│  Firestore   │
│  Issues     │           │   Service    │           │  (Embeddings)│
└──────┬──────┘           └──────┬───────┘           └──────────────┘
       │                         │                          ▲
       │                         ▼                          │
       │                  ┌──────────────┐                  │
       ├─────────────────►│ Vertex AI    │                  │
       │                  │ Agent Engine │                  │
       │                  └──────┬───────┘                  │
       │                         │                          │
       │                         ▼                          │
       │                  ┌──────────────┐           ┌──────┴───────┐
       └─────────────────►│ GitHub API   │───agent───►│ Vector-Based │
                          │ (Folder      │◄───OR─────►│ Agent        │
                          │  Traversal)  │           └──────────────┘
                          └──────┬───────┘
                                 │
                                 ▼
                          ┌──────────────┐
                          │  Pull        │
                          │  Requests    │
                          └──────────────┘
```

## 🔎 Agent Types

This project provides two different agent implementations:

### 1. Folder-Based Agent (`agent-folder.py`)
- Uses GitHub's API to traverse files similar to a human developer
- Explores directories and files sequentially
- No vector embeddings or Firebase required
- More exhaustive search but potentially slower on large codebases

### 2. Vector-Based Agent (`agent-vector.py`)
- Uses vector embeddings to quickly find relevant code
- Requires Firebase for storing code embeddings
- Webhook maintains up-to-date embeddings as code changes
- More efficient on large codebases with many files

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- GitHub account with access to create repos and webhooks
- Google Cloud Project with Vertex AI access
- Firestore database (only required for vector-based agent)

### Installation

1. **Agent Setup:**
   ```bash
   cd agent
   pip install -r requirements.txt
   ```

2. **Webhook Setup:**
   ```bash
   cd webhook
   pip install -r requirements.txt
   ```

3. **Environment Configuration:**
   Create a `.env` file with the following variables:
   ```
   GITHUB_TOKEN=your_github_token
   GITHUB_APP_ID=your_app_id                 # Optional for GitHub App
   GITHUB_PRIVATE_KEY_PATH=path_to_key.pem   # Optional for GitHub App
   GITHUB_INSTALLATION_ID=installation_id    # Optional for GitHub App
   AGENT_ENGINE=your_reasoning_engine_id
   ```

4. **Firestore Vector Configuration (only for vector-based agent):**
   ```bash
   gcloud firestore indexes composite create \
   --collection-group=code-embeddings \
   --query-scope=COLLECTION \
   --field-config field-path=embedding,vector-config='{"dimension":"256", "flat": {}}' \
   --database="(default)"
   ```

## 🔧 Usage

### Running the Folder-Based Agent

```bash
cd agent
python agent-folder.py --repo "username/repository" --issue 123
```

### Running the Vector-Based Agent

```bash
cd agent
python agent-vector.py --repo "username/repository" --issue 123
```

### Agent Demo UI

```bash
cd agent/demo
python demo.py
```

### Deploying the Webhook (for vector-based agent)

```bash
cd webhook
gcloud builds submit --config cloudbuild.yaml
```

### Webhook Configuration

Configure your GitHub repository to send webhook events to the deployed endpoint:
```
https://github-webhook-[hash].run.app/webhook
```

Set webhook to trigger on "Issues" and "Push" events.

### Viewing Webhook Logs

```bash
gcloud beta run services logs read github-webhook
gcloud beta run services logs tail github-webhook
```

## 📚 Components

### Agent Module

The agent connects to GitHub, analyzes issues, and implements solutions:

- `agent-folder.py`: Folder traversal agent using GitHub API
- `agent-vector.py`: Vector search agent using code embeddings
- `remote.py`: Core agent logic and Vertex AI integration
- `githubtools.py`: GitHub API integration

### Webhook Service

The webhook handles GitHub events and manages code embeddings:

- `webhook.py`: HTTP server for GitHub events
- Automatically runs in response to new issues and code changes
- Updates the vector database of code embeddings (required for agent-vector)

### Firebase

- Used only by the vector-based agent
- Stores code embeddings for efficient code search
- Updated automatically by the webhook service

## 💡 Future Ideas

- Add code execution to test if fixes successfully pass all tests
- Implement automatic code review for PRs
- Support additional repository platforms beyond GitHub

## 🔒 Security

- Store GitHub tokens and keys securely
- Use GitHub Apps with limited permissions when possible
- Deploy webhook behind authentication 

## 🤝 Contributing

Contributions welcome! Please open an issue to discuss changes before submitting PRs.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.