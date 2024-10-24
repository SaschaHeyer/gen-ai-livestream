import vertexai

from vertexai.generative_models import GenerationConfig, GenerativeModel

vertexai.init(project="sascha-playground-doit", location="us-central1")

model = GenerativeModel("gemini-1.5-pro")

response_schema = {"type": "STRING", "enum": ["high", "medium", "low"]}

prompt = """
The server is down, and our entire team is unable to work.
This needs to be fixed immediately
"""

response = model.generate_content(
    prompt,
    generation_config=GenerationConfig(
        response_mime_type="text/x.enum", response_schema=response_schema
    ),
)

print(response.text)