import vertexai

from vertexai.generative_models import GenerativeModel

vertexai.init(project="sascha-playground-doit", location="us-central1")

model = GenerativeModel("gemini-1.5-flash-001")

prompt = "Tell me something about Google that no one knows?"
response = model.generate_content(
    prompt,
    # Example Labels
    labels={
        "customer": "DoiT"
    },
)

print(response.text)
