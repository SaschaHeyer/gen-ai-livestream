from vertexai.preview import rag
import vertexai

# Project and corpus details
PROJECT_ID = "sascha-playground-doit"  # Update with your project ID
rag_corpus_id = "6622543252048314368"  # The corpus ID
corpus_name = f"projects/{PROJECT_ID}/locations/us-central1/ragCorpora/{rag_corpus_id}"

# Initialize Vertex AI API
vertexai.init(project=PROJECT_ID, location="us-central1")

# List and count files in the RAG corpus
try:
    files = rag.list_files(corpus_name=corpus_name)
    file_list = list(files)  # Convert to a list
    file_count = len(file_list)
    print(f"Number of files in the corpus: {file_count}")

    # Optionally, print details about each file
    #for file in file_list:
    #    print(file)
except Exception as e:
    print(f"Failed to retrieve files from the corpus: {e}")
