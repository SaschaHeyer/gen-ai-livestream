import vertexai

from vertexai.preview import rag
from vertexai.preview.generative_models import GenerativeModel, Tool

rag_corpus_id = "projects/234439745674/locations/us-central1/ragCorpora/569705352862367744"

vertexai.init(project="sascha-playground-doit", location="us-central1")

rag_retrieval_tool = Tool.from_retrieval(
        retrieval=rag.Retrieval(
            source=rag.VertexRagStore(
                rag_resources=[
                    rag.RagResource(
                        rag_corpus=rag_corpus_id
                    )
                ],
                similarity_top_k=3,  
                vector_distance_threshold=0.5,  
            ),
        )
)

rag_model = GenerativeModel(
        model_name="gemini-1.5-flash-001", tools=[rag_retrieval_tool]
    )

response = rag_model.generate_content("How do I install the LED light strip?")
print(response.text)