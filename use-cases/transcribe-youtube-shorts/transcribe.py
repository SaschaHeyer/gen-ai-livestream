import base64
import vertexai
import pandas as pd
from vertexai.generative_models import GenerativeModel, Part, SafetySetting
import time
import math

# Initialize Vertex AI
vertexai.init(project="sascha-playground-doit", location="us-central1")

# Function to generate transcript from YouTube video
def generate_transcript(video_uri):
    model = GenerativeModel("gemini-1.5-flash-002")
    
    video_part = Part.from_uri(
        mime_type="video/*",
        uri=video_uri
    )

    generation_config = {
        "max_output_tokens": 8192,
        "temperature": 1,
        "top_p": 0.95,
    }

    safety_settings = [
        SafetySetting(
            category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=SafetySetting.HarmBlockThreshold.OFF
        ),
        SafetySetting(
            category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=SafetySetting.HarmBlockThreshold.OFF
        ),
        SafetySetting(
            category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=SafetySetting.HarmBlockThreshold.OFF
        ),
        SafetySetting(
            category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=SafetySetting.HarmBlockThreshold.OFF
        ),
    ]

    responses = model.generate_content(
        ["transcribe this video", video_part],
        generation_config=generation_config,
        safety_settings=safety_settings,
        stream=True,  # Streaming the content to get it as it generates
    )

    transcript = ""
    for response in responses:
        transcript += response.text
    
    return transcript

# Load the CSV file
df = pd.read_csv('clips.csv')

# Add a progress indicator and save transcripts after each is processed
total_videos = len(df)
output_path = 'Clips_with_Transcripts.csv'

for idx, row in df.iterrows():
    youtube_url = row['YouTube URL']
    existing_transcript = row['Transcript']

    # Check if the transcript is already present (non-empty or non-NaN)
    if pd.notna(existing_transcript) and existing_transcript.strip() != "":
        print(f"Skipping video {idx + 1}/{total_videos}: Transcript already exists.")
        continue  # Skip this video as it already has a transcript

    # Generate the transcript for the current video
    print(f"Processing video {idx + 1}/{total_videos}: {youtube_url}")
    try:
        transcript = generate_transcript(youtube_url)
        df.at[idx, 'Transcript'] = transcript  # Save the transcript in the DataFrame

        # Save the CSV after each transcript is processed
        df.to_csv(output_path, index=False)
        print(f"Transcript for video {idx + 1} saved successfully.")
        
    except Exception as e:
        print(f"Error processing video {idx + 1}: {e}")
        # Optionally: You can add some delay to retry logic here
        time.sleep(2)

print(f"Final CSV saved at: {output_path}")
