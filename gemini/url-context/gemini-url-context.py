from google import genai
from google.genai.types import Tool, GenerateContentConfig

client = genai.Client(vertexai=True, project="sascha-playground-doit", location="global")
model_id = "gemini-2.5-flash"

tools = [
  {"url_context": {}},
]

url1 = "https://cloud.google.com/blog/products/ai-machine-learning"

response = client.models.generate_content(
    model=model_id,
    contents=f"What are the top 3 new blog entries on the google cloud blog {url1}.",
    config=GenerateContentConfig(
        tools=tools,
    )
)

for each in response.candidates[0].content.parts:
    print(each.text)

# For verification, you can inspect the metadata to see which URLs the model retrieved
print(response.candidates[0].url_context_metadata)
