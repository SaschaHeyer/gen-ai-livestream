
from vertexai.preview import rag
import vertexai

PROJECT_ID = "sascha-playground-doit"  # Update with your project ID
rag_corpus_id = "3918694625765752832"  # The corpus ID
corpus_name = f"projects/{PROJECT_ID}/locations/us-central1/ragCorpora/{rag_corpus_id}"




# Initialize Vertex AI API once per session
vertexai.init(project=PROJECT_ID, location="us-central1")

files = rag.list_files(corpus_name=corpus_name)
for file in files:
    print(file.display_name)
    print(file.name)


# Extract and print the last IDs as an array
file_ids = [file.name.split("/")[-1] for file in files]
print(file_ids)
print(len(file_ids))