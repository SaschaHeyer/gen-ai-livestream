import logging
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Firestore Client
firestore_client = firestore.Client()
collection = firestore_client.collection("code-embeddings")  # Change collection name if needed

# Initialize Vertex AI Embedding Model
model = TextEmbeddingModel.from_pretrained("text-embedding-005")


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


def store_embedding(file_path: str, file_content: str):
    """Stores the file embedding in Firestore."""
    embedding_vector = generate_embedding(file_content)

    if not embedding_vector:
        logger.error(f"❌ Skipping storage for {file_path}, embedding failed.")
        return

    doc = {
        "file_path": file_path,
        "content": file_content[:500],  # Store first 500 chars for reference
        "embedding": Vector(embedding_vector),
    }

    collection.add(doc)
    logger.info(f"✅ Stored embedding for {file_path} in Firestore.")


if __name__ == "__main__":
    # Example Test
    test_file_path = "math.py"
    test_content = "def sum(a, b):\n    print(a+b)"

    store_embedding(test_file_path, test_content)
