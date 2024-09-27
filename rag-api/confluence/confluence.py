import vertexai
from vertexai.preview import rag
from langchain.document_loaders import ConfluenceLoader
from google.cloud import storage
from vertexai.generative_models import GenerativeModel, Tool
import os
import json
from urllib.parse import urljoin
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve environment variables
token = os.getenv("CONFLUENCE_API_TOKEN")
username = os.getenv("CONFLUENCE_API_USERNAME")
url = os.getenv("CONFLUENCE_API_URL")  # Base URL, e.g., 'https://sascha-demo.atlassian.net/wiki'
project_id = os.getenv("PROJECT_ID")
region = os.getenv("REGION")
bucket_name = os.getenv("BUCKET_NAME")

if not token:
    raise ValueError("Confluence API token not found in environment variables.")
if not username:
    raise ValueError("Confluence API username not found in environment variables.")
if not url:
    raise ValueError("Confluence API URL not found in environment variables.")
if not project_id:
    raise ValueError("Project ID not found in environment variables.")
if not region:
    raise ValueError("Region not found in environment variables.")
if not bucket_name:
    raise ValueError("Bucket name not found in environment variables.")

# Set up Confluence API access
loader = ConfluenceLoader(
    url=url,
    username=username,
    api_key=token,
    cloud=True
)

print(f"Load pages")
# Load content from Confluence (playbooks or other content)
pages = loader.load(space_key="MFS")

# Process pages to include metadata (like page URL)
documents = []
for page in pages:
    print(page)
    # Use urljoin to properly construct the full page URL
    document = {
        "content": page.page_content,
        "metadata": {
            "title": page.metadata["title"],
            "url": page.metadata['source']
        }
    }
    documents.append(document)
    #print(document)

print(f"Found {len(documents)} pages")

# Initialize Vertex AI
vertexai.init(project=project_id, location=region)

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

# Initialize Google Cloud Storage client
storage_client = storage.Client()

# Get the bucket where you'll upload the files
bucket = storage_client.get_bucket(bucket_name)

# Temporary directory to store files locally before uploading
local_temp_dir = "/tmp/confluence_files"
os.makedirs(local_temp_dir, exist_ok=True)

# Iterate over Confluence content and save as JSON files (content + metadata)
file_paths = []
for idx, doc in enumerate(documents):
    file_name = f"document_{idx}.json"
    file_path = os.path.join(local_temp_dir, file_name)
    
    # Write the content and metadata as JSON to a temporary file
    with open(file_path, "w") as f:
        json.dump(doc, f)
    
    # Upload the JSON file to GCS
    blob = bucket.blob(f"confluence/{file_name}")
    blob.upload_from_filename(file_path)
    
    # Save the GCS path
    gcs_path = f"gs://{bucket_name}/confluence/{file_name}"
    print(f"Uploaded {file_name} to {gcs_path}")

# Now import those files into the RAG corpus
import_files_response = rag.import_files(corpus_name=corpus_name,  paths=[f"gs://{bucket_name}/confluence"], chunk_size=500)
print(f"Imported files to corpus: {import_files_response}")

# Retrieve the corpus to ensure files are added
corpus = rag.get_corpus(name=corpus_name)
print(f"Corpus Details: {corpus}")

# Create the retrieval tool
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

# Set up the generative model using Gemini
rag_model = GenerativeModel(
    model_name="gemini-1.5-flash-002", tools=[rag_retrieval_tool]
)

# Generate an answer with references to the Confluence page URLs
response = rag_model.generate_content("Summarize the company policy?")

print(f"Generated Answer: {response.text}")
