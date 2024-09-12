from vertexai.preview import rag
import vertexai

# Project and corpus details
PROJECT_ID = "sascha-playground-doit"  # Your project ID
rag_corpus_id = "6622543252048314368"  # Your corpus ID
corpus_name = f"projects/{PROJECT_ID}/locations/us-central1/ragCorpora/{rag_corpus_id}"

# Initialize Vertex AI API
vertexai.init(project=PROJECT_ID, location="us-central1")

# List and delete all files in the RAG corpus
try:
    # Step 1: List all files in the corpus
    files = rag.list_files(corpus_name=corpus_name)
    file_list = list(files)  # Convert pager to a list
    file_count = len(file_list)

    if file_count > 0:
        print(f"Number of files in the corpus: {file_count}")
        
        # Step 2: Iterate over each file and delete it
        for file in file_list:
            file_name = file.name  # Full path of the file in the corpus
            try:
                rag.delete_file(name=file_name)
                print(f"File {file_name} deleted successfully.")
            except Exception as delete_error:
                print(f"Failed to delete file {file_name}: {delete_error}")

    else:
        print("No files found in the corpus.")

except Exception as e:
    print(f"Failed to retrieve files from the corpus: {e}")
