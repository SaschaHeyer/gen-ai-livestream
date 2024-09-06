import vertexai

from vertexai.preview.generative_models import (
    GenerationConfig,
    GenerativeModel,
    Tool,
    grounding,
)

PROJECT_ID = "sascha-playground-doit"

vertexai.init(project=PROJECT_ID, location="us-central1")

model = GenerativeModel("gemini-1.5-flash-001")

data_store_id = "projects/sascha-playground-doit/locations/global/collections/default_collection/dataStores/sascha-grounding"

tool = Tool.from_retrieval(
    grounding.Retrieval(
        grounding.VertexAISearch(
            datastore=data_store_id,
            project=PROJECT_ID,
            location="global",
        )
    )
)

prompt = "Tell me all about Sascha Heyer"
response = model.generate_content(
    prompt,
    tools=[tool],
    generation_config=GenerationConfig(
        temperature=0.0,
    ),
)

print(response.text)