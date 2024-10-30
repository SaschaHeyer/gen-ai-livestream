import streamlit as st
import os
import json
import shutil
import re
import requests
from google.cloud import texttospeech
from pydub import AudioSegment
from vertexai.generative_models import GenerativeModel, GenerationConfig
import vertexai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Streamlit configuration
st.set_page_config(page_title="Podcast Generator", layout="wide")
st.title("🎙️ Podcast Generator")

# System prompt for Vertex AI
system_prompt = """you are an experienced podcast host...
- based on text like an article you can create an engaging conversation between two people.
- make the conversation at least 30000 characters long with a lot of emotion.
- in the response for me to identify use Sascha and Marina.
- Sascha is writing the articles and Marina is the second speaker that is asking all the good questions.
- The podcast is called The Machine Learning Engineer.
- Short sentences that can be easily used with speech synthesis.
- excitement during the conversation.
- do not mention last names.
- Sascha and Marina are doing this podcast together. Avoid sentences like: "Thanks for having me, Marina!"
- Include filler words like äh to make the conversation more natural.
"""

# Google TTS Client
client = texttospeech.TextToSpeechClient()
speaker_voice_map = {
    "Sascha": "ElevenLabs",
    "Marina": "en-US-Journey-O"
}

# Retrieve ElevenLabs API key from environment
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
elevenlabs_url = "https://api.elevenlabs.io/v1/text-to-speech/ERL3svWBAQ18ByCZTr4k"
elevenlabs_headers = {
    "Accept": "audio/mpeg",
    "Content-Type": "application/json",
    "xi-api-key": elevenlabs_api_key
}

# Google TTS function
def synthesize_speech_google(text, speaker, index):
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name=speaker_voice_map[speaker]
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16
    )
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    filename = f"audio-files/{index}_{speaker}.mp3"
    with open(filename, "wb") as out:
        out.write(response.audio_content)

# ElevenLabs TTS function
def synthesize_speech_elevenlabs(text, speaker, index):
    data = {
        "text": text,
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    response = requests.post(elevenlabs_url, json=data, headers=elevenlabs_headers)
    filename = f"audio-files/{index}_{speaker}.mp3"
    with open(filename, "wb") as out:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                out.write(chunk)

# Function to synthesize speech based on the speaker
def synthesize_speech(text, speaker, index):
    if speaker == "Sascha":
        synthesize_speech_elevenlabs(text, speaker, index)
    else:
        synthesize_speech_google(text, speaker, index)

# Function to sort filenames naturally
def natural_sort_key(filename):
    return [int(text) if text.isdigit() else text for text in re.split(r'(\d+)', filename)]

# Function to merge audio files
def merge_audios(audio_folder, output_file):
    combined = AudioSegment.empty()
    audio_files = sorted(
        [f for f in os.listdir(audio_folder) if f.endswith(".mp3") or f.endswith(".wav")],
        key=natural_sort_key
    )
    for filename in audio_files:
        audio_path = os.path.join(audio_folder, filename)
        audio = AudioSegment.from_file(audio_path)
        combined += audio
    combined.export(output_file, format="mp3")

# Vertex AI configuration to generate the conversation
generation_config = GenerationConfig(
    max_output_tokens=8192,
    temperature=1,
    top_p=0.95,
    response_mime_type="application/json",
    response_schema={"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"speaker": {"type": "STRING"}, "text": {"type": "STRING"}}}},
)

# Function to calculate costs based on token counts
def calculate_cost(prompt_token_count, candidates_token_count):
    cost_per_1k_chars = 0.0000046875
    total_chars = prompt_token_count + candidates_token_count
    total_cost = (total_chars / 1000) * cost_per_1k_chars
    return total_cost

# Function to generate the conversation using Vertex AI
def generate_conversation(article):
    vertexai.init(project="sascha-playground-doit", location="us-central1")
    model = GenerativeModel("gemini-1.5-flash-002", system_instruction=[system_prompt])
    responses = model.generate_content([article], generation_config=generation_config, stream=False)
    
    json_response = responses.candidates[0].content.parts[0].text
    json_data = json.loads(json_response)
    return json_data

# Function to generate the podcast audio from conversation data
def generate_audio(conversation):
    if os.path.exists('audio-files'):
        shutil.rmtree('audio-files')
    os.makedirs('audio-files', exist_ok=True)
    
    for index, part in enumerate(conversation):
        speaker = part['speaker']
        text = part['text']
        synthesize_speech(text, speaker, index)
    
    output_file = "podcast.mp3"
    merge_audios("audio-files", output_file)
    return output_file

# Streamlit inputs and outputs
article = st.text_area("Article Content", "Paste the article text here", height=300)
if st.button("Generate Podcast"):
    if not article:
        st.error("Please enter article content to generate a podcast.")
    else:
        with st.spinner("Generating conversation..."):
            conversation = generate_conversation(article)
        
        st.success("Conversation generated successfully!")
        st.json(conversation)
        
        # Generate audio files
        with st.spinner("Synthesizing audio..."):
            podcast_file = generate_audio(conversation)
        
        st.success("Audio synthesis complete!")
        st.audio(podcast_file, format="audio/mp3")
        st.download_button("Download Podcast", data=open(podcast_file, "rb"), file_name="podcast.mp3", mime="audio/mp3")
