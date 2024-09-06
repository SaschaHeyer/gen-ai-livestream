import vertexai

from vertexai.generative_models import (
    GenerationConfig,
    GenerativeModel,
    Tool,
    grounding,
)

# TODO (developer): update project_id
vertexai.init(project="sascha-playground-doit", location="us-central1")

model = GenerativeModel("gemini-1.5-flash-001")

# Use Google Search for grounding
tool = Tool.from_google_search_retrieval(grounding.GoogleSearchRetrieval())

prompt = "Whats the Google stock price?"
response = model.generate_content(
    prompt,
    tools=[tool],
    generation_config=GenerationConfig(
        temperature=0.0,
    ),
)

print(response.text)