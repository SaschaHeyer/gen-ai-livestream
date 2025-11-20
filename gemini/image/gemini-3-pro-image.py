from IPython.display import Image, Markdown, display
from google import genai
from google.genai.types import GenerateContentConfig, Part, ImageConfig, FinishReason
import os

PROJECT_ID = "sascha-playground-doit"
LOCATION = "global"

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
MODEL_ID = "gemini-3-pro-image-preview"

prompt = """
A person standing on a porch in front of a alone house in the wildernes. in the behind mountains sourrunded by clouds and fog.
"""
response = client.models.generate_content(
  model=MODEL_ID,
  contents=prompt,
  config=GenerateContentConfig(
      response_modalities=['IMAGE', 'TEXT'],
      image_config=ImageConfig(
          aspect_ratio="16:9",
          image_size="4K",
      ),
  ),
)

# Check for errors if an image is not generated
if response.candidates[0].finish_reason != FinishReason.STOP:
  reason = response.candidates[0].finish_reason
  raise ValueError(f"Prompt Content Error: {reason}")

for part in response.candidates[0].content.parts:
  if part.thought:
      continue # skip displaying thoughts
  if part.inline_data:
      display(Image(data=part.inline_data.data, width=1000))
