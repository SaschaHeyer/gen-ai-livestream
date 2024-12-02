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

# Additional import for AWS Bedrock
import boto3

# AWS Bedrock client setup
session = boto3.Session(region_name='us-west-2')  # Adjust your region
bedrock = session.client(service_name='bedrock-runtime')

# Load environment variables from .env file
load_dotenv()

# Initialize argument parser
parser = argparse.ArgumentParser(description='Generate podcast audio with different synthesis modes')
parser.add_argument(
    '--synthesis_mode', 
    choices=['default', 'multispeaker', 'polly'], 
    default='default', 
    help='Choose synthesis mode: default (ElevenLabs+Google), multispeaker (Google), or polly (AWS Polly)'
)

# Add command-line argument for using Bedrock
parser.add_argument('--use_bedrock', action='store_true', help='Use Amazon Bedrock with Anthropic')


args = parser.parse_args()

# Clients
tts_client = texttospeech.TextToSpeechClient()
tts_beta_client = texttospeech_v1beta1.TextToSpeechClient()

re_invent_system_prompt = """you are an experienced podcast host

Follow these instructions precisely:
1. based on text like an article you can create an engaging conversation between two people. 
2. make the conversation at least 30000 characters long with a lot of emotion.
3. in the response for me to identify use Sascha and Ieva.
4. Sascha and Ieva are doing this podcast together. 
5. Ieva is the second speaker that is asking all the good questions.
6. The podcast covers all topics about AWS re invent 2024 event
7. the podcast is called AWS insiders podcast sponsored by do it.
8. Short sentences that can be easily used with speech synthesis.
9. excitement during the conversation.
10. Include filler words like äh to make the conversation more natural.
11. only use the content provided.
"""

system_prompt = """you are an experienced podcast host

Follow these instructions precisely:
1. based on text like an article you can create an engaging conversation between two people. 
2. make the conversation at least 30000 characters long with a lot of emotion.
3. in the response for me to identify use Sascha and Ieva.
4. Sascha and Ieva are doing this podcast together. 
5. Ieva is the second speaker that is asking all the good questions.
6. The podcast covers all topics about AWS
7. the podcast is called AWS insiders podcast sponsored by do it.
8. Short sentences that can be easily used with speech synthesis.
9. excitement during the conversation.
10. Include filler words like äh to make the conversation more natural.
11. only use the content provided.
"""

POLLY_VOICE_CONFIG = {
    "Sascha": "Stephen",
    "Ieva": "Danielle"
}

# Speaker configurations
DEFAULT_SPEAKER_CONFIG = {
    "Sascha": "ElevenLabs",  # ElevenLabs API
    "Ieva": "en-US-Journey-O" 
}

MULTISPEAKER_CONFIG = {
    "Sascha": "U",  
    "Ieva": "R"
}

# ElevenLabs configuration
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
elevenlabs_url = "https://api.elevenlabs.io/v1/text-to-speech/ERL3svWBAQ18ByCZTr4k"
elevenlabs_headers = {
    "Accept": "audio/mpeg",
    "Content-Type": "application/json",
    "xi-api-key": elevenlabs_api_key
}

# Tool definition for Bedrock
tool_list = [
    {
        "toolSpec": {
            "name": "generate_podcast",
            "description": "Generate a podcast conversation between two speakers.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "conversation": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "speaker": {
                                        "type": "string",
                                        "description": "Name of the speaker."
                                    },
                                    "text": {
                                        "type": "string",
                                        "description": "Speech text for the speaker."
                                    }
                                },
                                "required": ["speaker", "text"]
                            }
                        }
                    },
                    "required": ["conversation"]
                }
            }
        }
    }
]

def synthesize_speech_g(text, speaker, index):
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

from boto3 import client

def synthesize_speech_polly(text, speaker, index):
    polly = client('polly', region_name='us-west-2')  # Adjust region as needed
    try:
        response = polly.synthesize_speech(
            Engine='neural',
            Text=text,
            OutputFormat='mp3',
            VoiceId=POLLY_VOICE_CONFIG[speaker]
        )
        stream = response.get('AudioStream')
        filename = f"audio-files/{index}_{speaker}.mp3"
        with open(filename, 'wb') as f:
            f.write(stream.read())
        print(f'Polly audio content written to file "{filename}"')
    except Exception as e:
        print(f"Error generating audio with Polly for speaker '{speaker}': {str(e)}")


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
        synthesize_speech_g(text, speaker, index)

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



def calculate_cost(prompt_token_count, candidates_token_count):
    cost_per_1k_chars = 0.0000046875
    total_chars = prompt_token_count + candidates_token_count
    total_cost = (total_chars / 1000) * cost_per_1k_chars
    return total_cost

def generate_conversation_bedrock(article):
    print("Using Amazon Bedrock for conversation generation...")
    message = {
        "role": "user",
        "content": [
            {"text": f"<content>{article}</content>"},
            {"text": system_prompt}
        ],
    }
    response = bedrock.converse(
        modelId="anthropic.claude-3-sonnet-20240229-v1:0",  # Adjust based on model availability
        messages=[message],
        inferenceConfig={
            "maxTokens": 4096,
            "temperature": 0.7
        },
        toolConfig={
            "tools": tool_list,
            "toolChoice": {
                "tool": {
                    "name": "generate_podcast"
                }
            }
        }
    )
    response_message = response['output']['message']
    response_content_blocks = response_message['content']
    content_block = next((block for block in response_content_blocks if 'toolUse' in block), None)
    tool_use_block = content_block['toolUse']
    conversation_data = tool_use_block['input']['conversation']  # Extract the conversation array

    return conversation_data


def generate_conversation(article):
    vertexai.init(project="sascha-playground-doit", location="us-central1")
    model = GenerativeModel(
        "gemini-1.5-flash-002",
        system_instruction=[system_prompt]
    )

    # Vertex AI configuration
    generation_config = GenerationConfig(
        max_output_tokens=8192,
        temperature=0.7,
        top_p=0.95,
        response_mime_type="application/json",
        response_schema={"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"speaker": {"type": "STRING"}, "text": {"type": "STRING"}}}},
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
    elif args.synthesis_mode == 'polly':
        if os.path.exists('audio-files'):
            shutil.rmtree('audio-files')
        os.makedirs('audio-files', exist_ok=True)
        for index, part in enumerate(conversation):
            speaker = part['speaker']
            text = part['text']
            synthesize_speech_polly(text, speaker, index)
    else:  # Default synthesis
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

def save_conversation(conversation):
    json_output_path = "./conversation/conversation.json"
    os.makedirs(os.path.dirname(json_output_path), exist_ok=True)
    with open(json_output_path, "w") as json_file:
        json.dump(conversation, json_file, indent=4)
    print(f"Conversation saved to {json_output_path}")

def main():
    # Read the article from the file
    with open('./articles/reinvent2024/intro2.txt', 'r') as file:
        article = file.read()

     # Decide which platform to use for generating conversation
    if args.use_bedrock:
        conversation = generate_conversation_bedrock(article)
    else:
        conversation = generate_conversation(article)

    save_conversation(conversation)

    generate_audio(conversation)

if __name__ == "__main__":
    main()