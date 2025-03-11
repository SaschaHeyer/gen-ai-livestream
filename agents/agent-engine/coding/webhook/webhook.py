import logging
import requests
import base64
import os
from flask import Flask, request, jsonify
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel
from dotenv import load_dotenv

import vertexai
from vertexai.preview import reasoning_engines

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Firestore Client
firestore_client = firestore.Client()
collection = firestore_client.collection("code-embeddings")

# Initialize Vertex AI Embedding Model
model = TextEmbeddingModel.from_pretrained("text-embedding-005")

# Get secrets from environment variables
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
AGENT_ENGINE = os.environ.get("AGENT_ENGINE")
app = Flask(__name__)

def analyze_issue(owner, repo, issue_number):
    """ Calls Vertex AI Reasoning Engine to analyze the GitHub issue. """
    # Check if agent engine is properly configured
    if not AGENT_ENGINE:
        logger.error("❌ Agent Engine ID not found in environment variables!")
        return "Error: Agent Engine configuration missing"

    remote_agent = reasoning_engines.ReasoningEngine(AGENT_ENGINE)

    response = remote_agent.query(
        input=f"Analyze and fix/implement the issue #{issue_number} in {owner}/{repo}"
    )

    return response["output"]

@app.route("/webhook", methods=["POST"])
def github_webhook():
    payload = request.json
    event = request.headers.get("X-GitHub-Event", "")

    logger.info(f"🔔 Received webhook event: {event}")

    if event == "issues" and payload.get("action") == "opened":
        issue_number = payload["issue"]["number"]
        issue_title = payload["issue"]["title"]
        issue_body = payload["issue"]["body"]
        repo_name = payload["repository"]["name"]
        repo_owner = payload["repository"]["owner"]["login"]

        logger.info(f"🐞 New GitHub Issue #{issue_number}: {issue_title}")
        logger.info(f"📝 Issue Description: {issue_body[:200]}...")

        response_text = analyze_issue(repo_owner, repo_name, issue_number)
        logger.info(f"🤖 Agent Engine Response: {response_text}")

    if event == "push":
        # Extract repo owner and name dynamically
        repository = payload.get("repository", {})
        repo_owner = repository.get("owner", {}).get("login", "")
        repo_name = repository.get("name", "")
        branch = payload.get("ref", "").replace("refs/heads/", "")

        if not repo_owner or not repo_name:
            logger.error("❌ Repository owner or name missing in webhook payload!")
            return jsonify({"error": "Repository details missing"}), 400

        # Only process pushes to main branch
        if branch != "main":
            return jsonify({"message": "Webhook ignored - not main branch"}), 200

        logger.info(f"📦 Repository: {repo_owner}/{repo_name} (branch: {branch})")

        changed_files = []
        removed_files = []  # Track deleted files

        for commit in payload.get("commits", []):
            changed_files.extend(commit.get("added", []))
            changed_files.extend(commit.get("modified", []))
            removed_files.extend(commit.get("removed", []))  # ✅ Handle deleted files

        logger.info(f"📂 Changed files: {changed_files}")
        logger.info(f"🗑️ Removed files: {removed_files}")

        # Process and store embeddings for modified/new files
        for file_path in changed_files:
            file_content = fetch_file_content(repo_owner, repo_name, file_path)
            if file_content:
                upsert_embedding(repo_owner, repo_name, file_path, file_content)

        # Handle file deletions
        for file_path in removed_files:
            delete_embedding(repo_owner, repo_name, file_path)

        return jsonify({"message": "Webhook processed"}), 200

    return jsonify({"message": "No action taken"}), 200


def fetch_file_content(repo_owner: str, repo_name: str, file_path: str) -> str:
    """Fetches the latest content of a file from GitHub."""
    # Check if GitHub token is properly configured
    if not GITHUB_TOKEN:
        logger.error("❌ GitHub token not found in environment variables!")
        return None

    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        file_data = response.json()
        if "content" in file_data:
            content = base64.b64decode(file_data["content"]).decode("utf-8")
            logger.info(f"📄 Fetched content for {file_path} ({len(content)} chars)")
            return content
    else:
        logger.error(f"❌ Failed to fetch {file_path}: {response.text}")
        return None


def generate_embedding(text: str) -> list[float]:
    """Generates an embedding vector using Google's Vertex AI API."""
    try:
        inputs = [TextEmbeddingInput(text, "RETRIEVAL_DOCUMENT")]
        embeddings = model.get_embeddings(inputs, output_dimensionality=256)
        embedding_vector = embeddings[0].values
        logger.info(f"🔢 Generated embedding of size {len(embedding_vector)}")
        return embedding_vector
    except Exception as e:
        logger.error(f"❌ Embedding generation failed: {str(e)}")
        return []


def upsert_embedding(repo_owner: str, repo_name: str, file_path: str, file_content: str):
    """Checks if a file exists in Firestore and updates or inserts it accordingly."""
    embedding_vector = generate_embedding(file_content)

    if not embedding_vector:
        logger.error(f"❌ Skipping storage for {file_path}, embedding failed.")
        return

    # Firestore document ID: Convert slashes to underscores to avoid Firestore path issues
    doc_id = f"{file_path}".replace("/", "_").replace("|", "_")

    doc_ref = collection.document(doc_id)
    doc_snapshot = doc_ref.get()

    if doc_snapshot.exists:
        # Update existing document
        doc_ref.update({
            "content": file_content[:500],  # Store first 500 chars for reference
            "embedding": Vector(embedding_vector),
        })
        logger.info(f"🔄 Updated embedding for {file_path} in Firestore.")
    else:
        # Insert new document
        doc_ref.set({
            "repo_owner": repo_owner,
            "repo_name": repo_name,
            "file_path": file_path,
            "content": file_content[:500],
            "embedding": Vector(embedding_vector),
        })
        logger.info(f"✅ Stored new embedding for {file_path} in Firestore.")


def delete_embedding(repo_owner: str, repo_name: str, file_path: str):
    """Deletes the embedding of a removed file from Firestore."""
    doc_id = f"{file_path}".replace("/", "_").replace("|", "_")

    doc_ref = collection.document(doc_id)
    doc_snapshot = doc_ref.get()

    if doc_snapshot.exists:
        doc_ref.delete()
        logger.info(f"🗑️ Deleted embedding for {file_path} from Firestore.")
    else:
        logger.info(f"⚠️ Tried to delete {file_path}, but it was not found in Firestore.")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
