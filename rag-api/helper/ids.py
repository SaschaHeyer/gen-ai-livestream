
from vertexai.preview import rag
import vertexai

PROJECT_ID = "sascha-playground-doit"  # Update with your project ID
rag_corpus_id = "3918694625765752832"  # The corpus ID
corpus_name = f"projects/{PROJECT_ID}/locations/us-central1/ragCorpora/{rag_corpus_id}"

# Initialize Vertex AI API once per session
vertexai.init(project=PROJECT_ID, location="us-central1")

response = rag.retrieval_query(
    rag_resources=[
        rag.RagResource(
            rag_corpus=corpus_name,
            # Optional: supply IDs from `rag.list_files()`.
            rag_file_ids=["5328192457911885348"], #equals winnie the pooh so peter pan should not be returned
            # rag_file_ids=['5328192446948463255', '5328192448058545451', '5328192449259346053', '5328192450169006952', '5328192450360784292', '5328192450453353140', '5328192451665738742', '5328192451994315833', '5328192452514673341', '5328192452815867042', '5328192453095168726', '5328192453690960379', '5328192455483789462', '5328192455848580312', '5328192456659753736', '5328192456707006489', '5328192457352485485', '5328192457558113319', '5328192458007120537', '5328192457911885348', '5328192493171760432']
        )
    ],
    text="Peter pan",
    similarity_top_k=10,  # Optional
    vector_distance_threshold=0.5,  # Optional
)
print(response)