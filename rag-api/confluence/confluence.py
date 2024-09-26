import vertexai
from vertexai.preview import rag
from langchain.document_loaders import ConfluenceLoader
from google.cloud import storage
from vertexai.generative_models import GenerativeModel, Tool
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve the Confluence API token from the environment
token = os.getenv("CONFLUENCE_API_TOKEN")

if not token:
    raise ValueError("Confluence API token not found in environment variables.")

# Initialize Vertex AI
vertexai.init(project="sascha-playground-doit", location="us-central1")

# Set up the embedding model config
embedding_model_config = rag.EmbeddingModelConfig(
    publisher_model="publishers/google/models/text-embedding-004"
)

# Create a new corpus for Confluence data
corpus_name = "DoiT Confluence Policies"
corpus = rag.create_corpus(display_name="RAG Confluence Demo", 
                           embedding_model_config=embedding_model_config)
corpus_name = corpus.name
print(f"Corpus created with name: {corpus_name}")

# Set up Confluence API access
loader = ConfluenceLoader(
    url="https://doitintl.atlassian.net/wiki/",
    username="sascha@doit.com",
    api_key=token,
    cloud=True
)

# Load content from Confluence (playbooks or other content)
pages = loader.load(label="cre-playbooks", limit=1000)

# Initialize Google Cloud Storage client
storage_client = storage.Client()

# Define the bucket name where you'll upload the files
bucket_name = "doit-llm"  # Replace with your GCS bucket name
bucket = storage_client.get_bucket(bucket_name)

# Temporary directory to store files locally before uploading
local_temp_dir = "/tmp/confluence_files"
os.makedirs(local_temp_dir, exist_ok=True)

# Iterate over Confluence content and save as text files
file_paths = []
for idx, page in enumerate(pages):
    file_name = f"playbook_{idx}.txt"
    file_path = os.path.join(local_temp_dir, file_name)
    
    # Write the content to a temporary text file
    with open(file_path, "w") as f:
        f.write(page.page_content)
    
    # Upload the file to GCS
    blob = bucket.blob(f"confluence/{file_name}")
    blob.upload_from_filename(file_path)
    
    # Save the GCS path
    gcs_path = f"gs://{bucket_name}/confluence/{file_name}"
    file_paths.append(gcs_path)
    print(f"Uploaded {file_name} to {gcs_path}")

# Now import those files into the RAG corpus
import_files_response = rag.import_files(corpus_name=corpus_name, paths=file_paths, chunk_size=500)
print(f"Imported files to corpus: {import_files_response}")

# Retrieve the corpus to ensure files are added
corpus = rag.get_corpus(name=corpus_name)
print(f"Corpus Details: {corpus}")

rag_retrieval_tool = Tool.from_retrieval(
        retrieval=rag.Retrieval(
            source=rag.VertexRagStore(
                rag_resources=[
                    rag.RagResource(
                        rag_corpus=corpus_name
                    )
                ],
                similarity_top_k=3,  
                vector_distance_threshold=0.5,  
            ),
        )
)

rag_model = GenerativeModel(
        model_name="gemini-1.5-flash-002", tools=[rag_retrieval_tool]
    )

response = rag_model.generate_content("Search Tuning in Vertex AI Search?")
print(response.text)