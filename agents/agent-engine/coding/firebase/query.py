import logging
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Firestore Client
firestore_client = firestore.Client()
collection = firestore_client.collection("code-embeddings")  # Adjust collection if needed

# Vertex AI Embedding Model
MODEL_NAME = "text-embedding-005"
DIMENSIONALITY = 256
model = TextEmbeddingModel.from_pretrained(MODEL_NAME)


def generate_embedding(text: str, task: str) -> list[float]:
    """Generates an embedding vector using Google's Vertex AI API."""
    try:
        inputs = [TextEmbeddingInput(text, task)]
        embeddings = model.get_embeddings(inputs, output_dimensionality=DIMENSIONALITY)
        embedding_vector = embeddings[0].values
        logger.info(f"🔢 Generated embedding of size {len(embedding_vector)} for query.")
        return embedding_vector
    except Exception as e:
        logger.error(f"❌ Embedding generation failed: {str(e)}")
        return []


def query_firestore(query_text: str):
    """Queries Firestore using vector search to find relevant code snippets and show similarity."""
    # Generate an embedding for the query
    query_embedding = generate_embedding(query_text, "CODE_RETRIEVAL_QUERY")
    if not query_embedding:
        logger.error("❌ Failed to generate query embedding.")
        return

    # Perform vector search in Firestore
    vector_query = collection.find_nearest(
        vector_field="embedding",
        query_vector=Vector(query_embedding),
        distance_measure=DistanceMeasure.COSINE,  # Euclidean distance (lower = more similar)
        limit=5,  # Retrieve top 5 most relevant results
        distance_result_field="vector_distance",  # ✅ This will store the similarity score in Firestore
    )

    logger.info("\n🔍 Firestore Vector Search Results:")
    for doc in vector_query.stream():
        result = doc.to_dict()
        similarity_score = doc.get("vector_distance")  # ✅ Correct way to retrieve similarity score

        logger.info(f"📄 File: {result.get('file_path')}")
        logger.info(f"💡 Code Snippet: {result.get('content')[:500]}")  # Show first 500 chars
        logger.info(f"🔢 Similarity Score (Euclidean Distance): {similarity_score:.4f}")
        logger.info("-" * 60)

    return vector_query


if __name__ == "__main__":
    # Test the vector search with a sample query
    test_query = "Retrieve a function that returns hello world"
    query_firestore(test_query)
