from typing import List
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel
import sqlite3
import sqlite_vec
import struct
import numpy as np
import matplotlib.pyplot as plt

# Embedding model constants
MODEL_NAME = "text-embedding-preview-0815"
DIMENSIONALITY = 256

# Function to embed text using Vertex AI for code or text retrieval
def embed_text(
    texts: List[str],
    task: str = "RETRIEVAL_DOCUMENT",
    model_name: str = MODEL_NAME,
    dimensionality: int = DIMENSIONALITY,
) -> List[List[float]]:
    """Embeds texts or code with a pre-trained, foundational model."""
    model = TextEmbeddingModel.from_pretrained(model_name)
    inputs = [TextEmbeddingInput(text, task) for text in texts]
    kwargs = dict(output_dimensionality=dimensionality) if dimensionality else {}
    embeddings = model.get_embeddings(inputs, **kwargs)
    return [embedding.values for embedding in embeddings]

# Function to serialize embeddings for SQLite
def serialize_f32(vector: List[float]) -> bytes:
    """Serializes a list of floats into a compact "raw bytes" format"""
    return struct.pack("%sf" % len(vector), *vector)

# Example code blocks (corpus)
code_blocks = [
    "def func(a, b): return a + b",
    "def func(a, b): return a - b",
    """# division.py
def divide(a, b):
    return a / b""",
]

# Embedding the code blocks
code_embeddings = embed_text(code_blocks, task="RETRIEVAL_DOCUMENT")

# Step 1: Vector Search
# =====================
# Connect to in-memory SQLite database
db = sqlite3.connect(":memory:")
db.enable_load_extension(True)
sqlite_vec.load(db)
db.enable_load_extension(False)

# Create the vector table with correct dimensionality (256)
db.execute("CREATE VIRTUAL TABLE vec_items USING vec0(embedding float[256])")

# Insert the code embeddings into the table
for i, embedding in enumerate(code_embeddings):
    db.execute(
        "INSERT INTO vec_items(rowid, embedding) VALUES (?, ?)",
        [i + 1, serialize_f32(embedding)]
    )

# Define a code query
query_code = ["Bug Report: There's an issue in the division function where dividing by zero causes the program to crash. Please fix this by handling the division by zero case."]

# Get the embedding of the query
query_embedding = embed_text(query_code, task="CODE_RETRIEVAL_QUERY")[0]

# Perform vector search for the query embedding in SQLite
rows = db.execute(
    """
    SELECT rowid, distance
    FROM vec_items
    WHERE embedding MATCH ?
    ORDER BY distance
    LIMIT 5
    """,
    [serialize_f32(query_embedding)],
).fetchall()

# Extract the scores and indices from the results
embedding_scores = [1 - row[1] for row in rows]  # Convert distance to similarity score
embedding_indices = [row[0] for row in rows]  # Retrieve the correct indices from the rows

# Display the matching code blocks based on similarity
matching_code_blocks = [code_blocks[i - 1] for i in embedding_indices]
print("Matching Code Blocks (ranked by similarity):")
for i, code in enumerate(matching_code_blocks):
    print(f"Rank {i+1}: {code}")

# Step 2: Plot the Results (Optional)
# ========================
# Plot the similarity scores for the matched code blocks
plt.figure(figsize=(10, 6))
x = np.arange(len(embedding_indices))
plt.barh(x, embedding_scores, color='skyblue')
plt.yticks(x, [f"Code Block {index}" for index in embedding_indices])
plt.xlabel('Similarity Score')
plt.title('Similarity Scores for Retrieved Code Blocks')
plt.gca().invert_yaxis()  # Invert y-axis for better readability
plt.tight_layout()

# Save the chart as a PNG file (optional)
plt.savefig('code_search_similarity_scores.png')

# Show the plot (optional)
plt.show()
