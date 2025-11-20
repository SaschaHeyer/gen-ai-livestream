from google import genai
from google.genai.types import GenerateContentConfig, Part, ImageConfig, FinishReason
from google.genai import types

PROJECT_ID = "sascha-playground-doit"
LOCATION = "global"

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
MODEL_ID = "gemini-3-pro-image-preview"

prompt = """
Replace the person on the left side of the robot with the person from the second image. do not change the persons look. """


with open("x1.png", "rb") as f:
    image1 = f.read()


with open("you.png", "rb") as f:
    image2 = f.read()

response = client.models.generate_content(
    model=MODEL_ID,
    contents=[
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
                Part.from_bytes(
                    data=image1,
                    mime_type="image/jpeg",
                ),
                Part.from_bytes(
                    data=image2,
                    mime_type="image/jpeg",
                ),
            ],
        )
    ],
    config=GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
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

image_parts = [part for part in response.candidates[0].content.parts if part.inline_data and not part.thought]

for idx, part in enumerate(image_parts, start=1):
    image = part.as_image()
    output_path = f"edited_image_{idx}.png"
    image.save(output_path)
    print(f"Saved: {output_path}")
