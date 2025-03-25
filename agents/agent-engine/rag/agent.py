import vertexai
from vertexai.preview import reasoning_engines
from vertexai.preview import rag
from vertexai.preview.generative_models import Tool

PROJECT_ID = "sascha-playground-doit"
LOCATION = "us-central1"
STAGING_BUCKET = "gs://doit-llm"

vertexai.init(project=PROJECT_ID, 
              location=LOCATION,
              staging_bucket=STAGING_BUCKET)

model = "gemini-1.5-flash-002"


def get_session_history(session_id: str):
    from langchain_google_firestore import FirestoreChatMessageHistory
    from google.cloud import firestore

    client = firestore.Client(project="sascha-playground-doit")
    return FirestoreChatMessageHistory(
        client=client,
        session_id=session_id,
        collection="history",
        encode_message=False,
    )


rag_retrieval_tool = Tool.from_retrieval(
    retrieval=rag.Retrieval(
        source=rag.VertexRagStore(
            rag_resources=[rag.RagResource(
                rag_corpus="projects/234439745674/locations/us-central1/ragCorpora/2842897264777625600")],
            similarity_top_k=3,
            vector_distance_threshold=0.5,
        ),
    )
)

agent = reasoning_engines.LangchainAgent(
    model_kwargs={"temperature": 0.2},
    model=model,
    chat_history=get_session_history,
    tools=[
        rag_retrieval_tool,
    ],
    enable_tracing=True,
)

remote_agent = reasoning_engines.ReasoningEngine.create(
    agent,
    requirements=[
        "google-cloud-aiplatform[langchain,reasoningengine]",
        "langchain-google-firestore"
    ],
)
