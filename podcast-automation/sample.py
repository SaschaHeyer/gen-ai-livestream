# Retrieve ElevenLabs API key from environment
import os
import requests
from dotenv import load_dotenv
load_dotenv()

elevenlabs_api_key_ieva = os.getenv("ELEVENLABS_API_KEY_IEVA")
elevenlabs_url_ieva = "https://api.elevenlabs.io/v1/text-to-speech/jvGRZ3PahgThaB8BsL3H"
elevenlabs_headers_ieva = {
    "Accept": "audio/mpeg",
    "Content-Type": "application/json",
    "xi-api-key": elevenlabs_api_key_ieva
}


api_url = elevenlabs_url_ieva  # New URL for Ieva
headers = elevenlabs_headers_ieva  # Reuse headers, as they're the same
    
    # Prepare the data payload
data = {
        "text": "Hi my name is Ieva",
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    
    # Make the API request
response = requests.post(api_url, json=data, headers=headers)
print(response)
filename = f"audio-files/sample.mp3"

with open(filename, "wb") as out:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                out.write(chunk)
print(f'Audio content written to file "{filename}"')