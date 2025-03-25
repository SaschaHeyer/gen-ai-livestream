import vertexai
from vertexai.preview import reasoning_engines

PROJECT_ID = "sascha-playground-doit"
LOCATION = "us-central1"
STAGING_BUCKET = "gs://doit-llm"

vertexai.init(project=PROJECT_ID,
              location=LOCATION,
              staging_bucket=STAGING_BUCKET)

model = "gemini-2.0-flash-exp"
#model = "gemini-1.5-flash-002"


def get_session_history(session_id: str):
    from langchain_google_firestore import FirestoreChatMessageHistory
    from google.cloud import firestore

    client = firestore.Client(project="sascha-playground-doit")
    return FirestoreChatMessageHistory(
        client=client,
        session_id=session_id,
        collection="history",
        encode_message=False,
        ttl_days=1 / 1440,
    )

agent = reasoning_engines.LangchainAgent(
    model_kwargs={"temperature": 0},
    model=model,
    chat_history=get_session_history,
)

response = agent.query(
    input="Hi my name is sascha",
    config={"configurable": {"session_id": "1"}})

print(response["output"])

response = agent.query(
    input="What is my name?",
    config={"configurable": {"session_id": "1"}})

print(response["output"])
