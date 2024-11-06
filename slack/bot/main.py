import os
import logging
import hashlib
import hmac
import time
import re
import requests
from flask import Flask, request, jsonify, abort
from dotenv import load_dotenv  # Import dotenv

# Import Vertex AI and Gemini model classes
import vertexai
from vertexai.preview import rag
from vertexai.preview.generative_models import GenerativeModel, Tool

load_dotenv()

app = Flask(__name__)

SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
RAG_CORPUS_ID = os.getenv("RAG_CORPUS_ID")

logging.basicConfig(level=logging.INFO)

# Initialize Vertex AI and Gemini model
vertexai.init(project=PROJECT_ID, location=LOCATION)
rag_retrieval_tool = Tool.from_retrieval(
    retrieval=rag.Retrieval(
        source=rag.VertexRagStore(
            rag_resources=[rag.RagResource(rag_corpus=RAG_CORPUS_ID)],
            similarity_top_k=3,
            vector_distance_threshold=0.5,
        ),
    )
)
rag_model = GenerativeModel(model_name="gemini-1.5-flash-001", tools=[rag_retrieval_tool])

def verify_slack_request(request):
    slack_signature = request.headers.get("X-Slack-Signature", "")
    slack_request_timestamp = request.headers.get("X-Slack-Request-Timestamp", "")

    if abs(time.time() - int(slack_request_timestamp)) > 60 * 5:
        logging.warning("Request timestamp is too old.")
        return False

    sig_basestring = f"v0:{slack_request_timestamp}:{request.get_data(as_text=True)}"
    my_signature = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(my_signature, slack_signature):
        logging.warning("Invalid Slack signature.")
        return False

    return True

def send_slack_message(channel_id, text):
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}"
    }
    data = {
        "channel": channel_id,
        "text": text
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        logging.error("Failed to send message: %s", response.text)
    else:
        logging.info("Message sent successfully: %s", response.json())

def generate_gemini_response(question):
    # Generate content using Gemini model
    response = rag_model.generate_content(question)
    return response.text

@app.route('/webhook', methods=['POST'])
def slack_webhook():
    data = request.get_json()

    if data.get("type") == "url_verification":
        return jsonify({"challenge": data.get("challenge")})

    if not verify_slack_request(request):
        abort(400, description="Request verification failed")

    if "event" in data:
        event_data = data["event"]

        # Only respond to app mentions
        if event_data.get("type") == "app_mention":
            user = event_data.get("user")
            channel = event_data.get("channel")
            text = event_data.get("text")  # Original text with mention

            # Remove the bot mention from the text
            cleaned_text = re.sub(r"<@U[0-9A-Z]+>", "", text).strip()

            # Generate response from Gemini
            gemini_response = generate_gemini_response(cleaned_text)

            # Send the Gemini response back to Slack
            send_slack_message(channel, gemini_response)

    return jsonify({'status': 'event received'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)