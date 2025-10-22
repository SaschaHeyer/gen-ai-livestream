from google import genai
from google.genai import types

# Only for videos of size <20Mb
video_file_name = "./sample/sample.mp4"
video_bytes = open(video_file_name, "rb").read()

client = genai.Client(
    vertexai=True, project="sascha-playground-doit", location="global"
)
model_id = "gemini-2.5-flash"

response = client.models.generate_content(
    model=model_id,
    contents=[
        types.Part(
            inline_data=types.Blob(data=video_bytes, mime_type="video/mp4"),
            video_metadata=types.VideoMetadata(fps=5),
        ),
    ],
)

for each in response.candidates[0].content.parts:
    print(each.text)

# For verification, you can inspect the metadata to see which URLs the model retrieved
print(response.candidates[0].url_context_metadata)
