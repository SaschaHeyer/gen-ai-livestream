from typing import List
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel
import sqlite3
import sqlite_vec
import struct
from google.cloud import discoveryengine_v1alpha as discoveryengine
import matplotlib.pyplot as plt
import numpy as np
import time  # Import the time module

# Function to embed text using Vertex AI
def embed_text(
    texts: List[str],
    task: str = "RETRIEVAL_DOCUMENT",
    model_name: str = "text-embedding-004",
) -> List[List[float]]:
    """Embeds texts with a pre-trained, foundational model."""
    model = TextEmbeddingModel.from_pretrained(model_name)
    inputs = [TextEmbeddingInput(text, task) for text in texts]
    embeddings = model.get_embeddings(inputs)
    return [embedding.values for embedding in embeddings]

# Function to serialize embeddings for SQLite
def serialize_f32(vector: List[float]) -> bytes:
    """Serializes a list of floats into a compact "raw bytes" format"""
    return struct.pack("%sf" % len(vector), *vector)

# Adjusted example sentences where only one text matches the query perfectly
sentences = [
    "Python is a popular programming language known for its simplicity and readability, making it a preferred choice for both beginners and experienced developers. Its clear syntax and the vast ecosystem of libraries allow for rapid development and easy maintenance of codebases. Furthermore, Python's community-driven development ensures continuous improvement and support.",
    "The Python snake is one of the largest species of snakes in the world, often recognized by its impressive size and strength. Found primarily in tropical regions of Africa and Asia, these non-venomous constrictors can grow to lengths exceeding 20 feet, making them formidable predators in their natural habitats. Despite their fearsome reputation, pythons are also known for their adaptability.",
    "In Greek mythology, Python was a monstrous serpent or dragon who dwelled in the caves of Mount Parnassus, terrorizing the inhabitants of the nearby city of Delphi. According to myth, Python was slain by the god Apollo, who sought revenge for the serpent's attempts to kill his mother, Leto, during her pregnancy. This act not only established Apollo's prowess but also laid the foundation for the establishment of the Oracle of Delphi.",
    "Python's extensive libraries and frameworks make it a versatile language for web development, offering powerful tools for building everything from simple websites to complex web applications. Frameworks like Django and Flask provide developers with a robust foundation for creating scalable, secure, and maintainable web services. Additionally, Python's compatibility with other technologies and its support for modern programming paradigms like asynchronous programming ensure that developers can efficiently handle the demands of today's web environments."
]

# Step 1: Vector Search
# =====================
# Get embeddings
embeddings = embed_text(sentences)

# Connect to in-memory SQLite database
db = sqlite3.connect(":memory:")
db.enable_load_extension(True)
sqlite_vec.load(db)
db.enable_load_extension(False)

# Create the vector table
db.execute("CREATE VIRTUAL TABLE vec_items USING vec0(embedding float[768])")

# Insert the embeddings into the table
for i, embedding in enumerate(embeddings):
    db.execute(
        "INSERT INTO vec_items(rowid, embedding) VALUES (?, ?)",
        [i + 1, serialize_f32(embedding)]
    )

# Define a query vector (embedding of the query sentence)
query_sentence = "Can python be used for web development?"
query_embedding = embed_text([query_sentence])[0]

# Search for all the embeddings with a LIMIT to ensure we retrieve all records
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

# Extract embedding-based similarity scores and their indices
embedding_scores = [1 - row[1] for row in rows]  # Convert distance to similarity score
embedding_indices = [row[0] for row in rows]  # Retrieve the correct indices from the rows

# Ensure that the ranking labels match the embedding order by sorting based on indices
embedding_labels = [f"Sentence {index}" for index in embedding_indices]

# Step 2: Ranking API
# ===================
# Replace with your project ID
project_id = "sascha-playground-doit"

# Initialize the Ranking API client
client = discoveryengine.RankServiceClient()

# Define the full resource name of the ranking config
ranking_config = client.ranking_config_path(
    project=project_id,
    location="global",
    ranking_config="default_ranking_config",
)

# Create the records directly from the sentences
ranking_records = [
    discoveryengine.RankingRecord(
        id=str(i + 1),
        title="",
        content=sentence
    ) for i, sentence in enumerate(sentences)
]

# Create the ranking request
ranking_request = discoveryengine.RankRequest(
    ranking_config=ranking_config,
    model="semantic-ranker-512@latest",
    top_n=5,
    query=query_sentence,
    records=ranking_records,
)

# Measure time before the ranking API call
start_time = time.time()

# Call the ranking API
ranking_response = client.rank(request=ranking_request)

# Measure time after the ranking API call
end_time = time.time()

# Calculate the duration in milliseconds
duration_ms = (end_time - start_time) * 1000
print(f"Time taken to rank documents: {duration_ms:.2f} milliseconds")

# Extract Ranking API scores
ranking_scores = [record.score for record in ranking_response.records]
ranking_labels = [f"Sentence {i+1}" for i in range(len(sentences))]  # Use consistent sentence indices

# Step 3: Plot the Results
# ========================
# Plotting the results side by side
plt.figure(figsize=(14, 10))  # Adjust figure size for better label visibility

x = np.arange(len(embedding_indices))  # the label locations (based on number of embeddings)
width = 0.35  # the width of the bars

fig, ax = plt.subplots()
rects1 = ax.barh(x - width/2, embedding_scores, width, label='Embedding Score')
rects2 = ax.barh(x + width/2, ranking_scores, width, label='Ranking API Score')

# Add some text for labels, title, and axes ticks
ax.set_xlabel('Scores')
ax.set_title('Comparison of Embedding Scores and Ranking API Scores')

# Use sentence indices as labels
ax.set_yticks(x)
ax.set_yticklabels(embedding_labels)  # Display the sentence indices as labels
ax.legend()

# Invert the y-axis so the highest score appears at the top
ax.invert_yaxis()

# Add the values on bars
def add_values(rects):
    for rect in rects:
        width = rect.get_width()
        ax.annotate(f'{width:.2f}',
                    xy=(width, rect.get_y() + rect.get_height() / 2),
                    xytext=(3, 0),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='left', va='center')

add_values(rects1)
add_values(rects2)

fig.tight_layout()

# Save the chart as a PNG file
plt.savefig('embedding_vs_ranking_scores_specific_with_indices.png')

# Show the plot (optional, useful for debugging)
plt.show()
