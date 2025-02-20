from typing import List, Dict
import sqlite3
import sqlite_vec
import struct
import matplotlib.pyplot as plt
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel

# Define structured data for events
events = [
    {"name": "Festival A", "date": "2024-07-05", "location": "Park Arena", "lineup": "Artists X, Y, Z"},
    {"name": "Grand Concert", "date": "2024-07-10", "location": "Concert Hall", "lineup": "Artists X, Y, Z"},
    {"name": "Festival A", "date": "2024-07-05", "location": "Park Arena", "lineup": "Artists X, Y, Z"},
    {"name": "Night Extravaganza", "date": "2024-07-10", "location": "City Square", "lineup": "Artists A, B, C"},
]

# Function to embed structured text using Vertex AI
def embed_text(
    texts: List[str],
    task: str = "RETRIEVAL_DOCUMENT",
    model_name: str = "text-embedding-004",
) -> List[List[float]]:
    model = TextEmbeddingModel.from_pretrained(model_name)
    inputs = [TextEmbeddingInput(text, task) for text in texts]
    embeddings = model.get_embeddings(inputs)
    return [embedding.values for embedding in embeddings]

# Function to serialize embeddings for SQLite
def serialize_f32(vector: List[float]) -> bytes:
    return struct.pack("%sf" % len(vector), *vector)

# Concatenate fields for embedding
def prepare_event_text(event: Dict[str, str]) -> str:
    return f"Event: {event['name']}, Date: {event['date']}, Location: {event['location']}, Lineup: {event['lineup']}"

# Embed and store each event
event_texts = [prepare_event_text(event) for event in events]
embeddings = embed_text(event_texts)

# Connect to SQLite and load the vector extension
db = sqlite3.connect(":memory:")
db.enable_load_extension(True)
sqlite_vec.load(db)
db.enable_load_extension(False)

# Create vector table
db.execute("CREATE VIRTUAL TABLE vec_items USING vec0(embedding float[768])")

# Insert embeddings into the table
for i, embedding in enumerate(embeddings):
    db.execute("INSERT INTO vec_items(rowid, embedding) VALUES (?, ?)", [i + 1, serialize_f32(embedding)])

# Query a structured event for duplicates
query_event = {"name": "Festival A", "date": "2024-07-05", "location": "Park Arena", "lineup": "Artists X, Y"}
query_text = prepare_event_text(query_event)
query_embedding = embed_text([query_text])[0]

# Search for duplicates
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

# Display duplicates with similarity scores
print("Detected Duplicates (Similarity Scores):")
for row in rows:
    event_index, similarity = row[0], 1 - row[1]
    print(f"Event: {event_texts[event_index - 1]}, Similarity Score: {similarity:.2f}")

# Optional visualization
plt.barh([f"Event {row[0]}" for row in rows], [1 - row[1] for row in rows])
plt.xlabel("Similarity Score")
plt.title("Event Similarity for Deduplication")
plt.gca().invert_yaxis()
plt.show()
