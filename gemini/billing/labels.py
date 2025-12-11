import vertexai

from vertexai.generative_models import GenerativeModel

vertexai.init(project="sascha-playground-doit", location="us-central1")

model = GenerativeModel("gemini-2.5-flash")

prompt = "Tell me something about Google that no one knows?"
response = model.generate_content(
    prompt,
    labels={
        "customer": "DoiT"
    },
)

print(response.text)
