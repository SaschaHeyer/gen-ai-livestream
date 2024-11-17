import base64
import json
import vertexai
import os
import re
import requests
import shutil
import argparse
from google.cloud import texttospeech, texttospeech_v1beta1
from pydub import AudioSegment
from vertexai.generative_models import GenerativeModel, GenerationConfig
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize argument parser
parser = argparse.ArgumentParser(description='Generate podcast audio with different synthesis modes')
parser.add_argument('--synthesis_mode', choices=['default', 'multispeaker'], 
                    default='default', help='Choose synthesis mode: default (ElevenLabs+Google) or multispeaker (Google)')
args = parser.parse_args()

# Clients
tts_client = texttospeech.TextToSpeechClient()
tts_beta_client = texttospeech_v1beta1.TextToSpeechClient()

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

# Speaker configurations
DEFAULT_SPEAKER_CONFIG = {
    "Sascha": "ElevenLabs",  # ElevenLabs API
    "Marina": "en-US-Journey-O"  # Google API
}

MULTISPEAKER_CONFIG = {
    "Sascha": "T",  # Using T for a male voice
    "Marina": "R"   # Using S for a female voice
}

# ElevenLabs configuration
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
elevenlabs_url = "https://api.elevenlabs.io/v1/text-to-speech/ERL3svWBAQ18ByCZTr4k"
elevenlabs_headers = {
    "Accept": "audio/mpeg",
    "Content-Type": "application/json",
    "xi-api-key": elevenlabs_api_key
}

def synthesize_speech_google(text, speaker, index):
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name=DEFAULT_SPEAKER_CONFIG[speaker]
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16
    )
    response = tts_client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    filename = f"audio-files/{index}_{speaker}.mp3"
    with open(filename, "wb") as out:
        out.write(response.audio_content)
    print(f'Audio content written to file "{filename}"')

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
    print(f'Audio content written to file "{filename}"')

def chunk_conversation(conversation, max_bytes=1000):  # Reduced to be even safer
    chunks = []
    current_chunk = []
    current_size = 0
    
    for turn in conversation:
        # Calculate byte size of the text
        text_size = len(turn['text'].encode('utf-8'))
        
        if current_size + text_size > max_bytes:
            # Store current chunk and start a new one
            if current_chunk:  # Only append if chunk is not empty
                chunks.append(current_chunk)
            current_chunk = [turn]
            current_size = text_size
        else:
            current_chunk.append(turn)
            current_size += text_size
    
    # Append the last chunk if it exists
    if current_chunk:
        chunks.append(current_chunk)
    
    print(f"Split conversation into {len(chunks)} chunks")
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i} size: {sum(len(turn['text'].encode('utf-8')) for turn in chunk)} bytes")
    
    return chunks

def synthesize_speech_multispeaker(conversation):
    # Create output directory if it doesn't exist
    if os.path.exists('audio-files'):
        shutil.rmtree('audio-files')
    os.makedirs('audio-files', exist_ok=True)
    
    # Split conversation into chunks
    conversation_chunks = chunk_conversation(conversation)
    
    # Process each chunk
    for chunk_index, chunk in enumerate(conversation_chunks):
        multi_speaker_markup = texttospeech_v1beta1.MultiSpeakerMarkup()
        
        for part in chunk:
            turn = texttospeech_v1beta1.MultiSpeakerMarkup.Turn()
            turn.text = part['text']
            turn.speaker = MULTISPEAKER_CONFIG[part['speaker']]
            multi_speaker_markup.turns.append(turn)
        
        synthesis_input = texttospeech_v1beta1.SynthesisInput(
            multi_speaker_markup=multi_speaker_markup
        )
        
        voice = texttospeech_v1beta1.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Studio-MultiSpeaker"
        )
        
        audio_config = texttospeech_v1beta1.AudioConfig(
            audio_encoding=texttospeech_v1beta1.AudioEncoding.MP3
        )
        
        try:
            response = tts_beta_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            # Save chunk to file
            chunk_filename = f"audio-files/chunk_{chunk_index}.mp3"
            with open(chunk_filename, "wb") as out:
                out.write(response.audio_content)
            print(f'Audio content written to file "{chunk_filename}"')
            
        except Exception as e:
            print(f"Error processing chunk {chunk_index}:")
            print(f"Chunk size: {sum(len(turn['text'].encode('utf-8')) for turn in chunk)} bytes")
            print(f"Number of turns: {len(chunk)}")
            print(f"Error: {str(e)}")
            raise e
    
    # Merge all chunks
    audio_folder = "./audio-files"
    output_file = "podcast.mp3"
    merge_audios(audio_folder, output_file)

def synthesize_speech_default(text, speaker, index):
    if speaker == "Sascha":
        synthesize_speech_elevenlabs(text, speaker, index)
    else:
        synthesize_speech_google(text, speaker, index)

def natural_sort_key(filename):
    return [int(text) if text.isdigit() else text for text in re.split(r'(\d+)', filename)]

def merge_audios(audio_folder, output_file):
    combined = AudioSegment.empty()
    audio_files = sorted(
        [f for f in os.listdir(audio_folder) if f.endswith(".mp3") or f.endswith(".wav")],
        key=natural_sort_key
    )
    for filename in audio_files:
        audio_path = os.path.join(audio_folder, filename)
        print(f"Processing: {audio_path}")
        audio = AudioSegment.from_file(audio_path)
        combined += audio
    combined.export(output_file, format="mp3")
    print(f"Merged audio saved as {output_file}")

# Vertex AI configuration
generation_config = GenerationConfig(
    max_output_tokens=8192,
    temperature=1,
    top_p=0.95,
    response_mime_type="application/json",
    response_schema={"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"speaker": {"type": "STRING"}, "text": {"type": "STRING"}}}},
)

def calculate_cost(prompt_token_count, candidates_token_count):
    cost_per_1k_chars = 0.0000046875
    total_chars = prompt_token_count + candidates_token_count
    total_cost = (total_chars / 1000) * cost_per_1k_chars
    return total_cost

def generate_conversation():
    vertexai.init(project="sascha-playground-doit", location="us-central1")
    model = GenerativeModel(
        "gemini-1.5-flash-002",
        system_instruction=[system_prompt]
    )
    responses = model.generate_content(
        [article],
        generation_config=generation_config,
        stream=False,
    )
    
    prompt_token_count = responses.usage_metadata.prompt_token_count
    candidates_token_count = responses.usage_metadata.candidates_token_count
    total_token_count = responses.usage_metadata.total_token_count
    
    total_cost = calculate_cost(prompt_token_count, candidates_token_count)
    print(f"Total token count: {total_token_count}")
    print(f"Cost for Gemini API usage: ${total_cost:.6f}")
    
    json_response = responses.candidates[0].content.parts[0].text
    json_data = json.loads(json_response)
    
    total_chars = sum(len(part["text"]) for part in json_data)
    print(f"Total character count in conversation: {total_chars}")
    
    formatted_json = json.dumps(json_data, indent=4)
    print(formatted_json)
    return json_data

def generate_audio(conversation):
    if args.synthesis_mode == 'multispeaker':
        synthesize_speech_multispeaker(conversation)
    else:
        if os.path.exists('audio-files'):
            shutil.rmtree('audio-files')
        
        os.makedirs('audio-files', exist_ok=True)
        for index, part in enumerate(conversation):
            speaker = part['speaker']
            text = part['text']
            synthesize_speech_default(text, speaker, index)
        
        audio_folder = "./audio-files"
        output_file = "podcast.mp3"
        merge_audios(audio_folder, output_file)

def main():
    # Read the article from the file
    with open('./articles/context-caching.txt', 'r') as file:
        global article
        article = file.read()
    
    # Generate conversation and audio
    conversation = generate_conversation()
    generate_audio(conversation)

if __name__ == "__main__":
    main()