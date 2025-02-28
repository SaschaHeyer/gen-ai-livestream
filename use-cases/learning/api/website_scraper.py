import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urlparse
from google.cloud import storage, firestore
from datetime import datetime
import json
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from pydub import AudioSegment
import shutil

# Google Cloud Configuration
BUCKET_NAME = "doit-llm"
BUCKET_FOLDER = "learning"
PODCAST_FOLDER = "podcasts"
storage_client = storage.Client()

MULTISPEAKER_CONFIG = {
    "Sascha": "U",
    "Ieva": "R"
}

def upload_to_gcs(file_path, filename, folder):
    """Upload a file to Google Cloud Storage bucket."""
    try:
        print(f"Uploading file: {file_path} as {filename} to GCS...")
        bucket = storage_client.bucket(BUCKET_NAME)
        destination_blob_name = f"{folder}/{filename}"
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(file_path, timeout=60)
        print(f"File uploaded successfully to: gs://{BUCKET_NAME}/{destination_blob_name}")
        return True, f"gs://{BUCKET_NAME}/{destination_blob_name}"
    except Exception as e:
        print(f"GCS Upload Error: {e}")
        return False, str(e)

def is_valid_url(url):
    """Validate if a URL is correctly formatted."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def scrape_website(url):
    """Scrape the content of a website."""
    try:
        print(f"Scraping content from {url}...")
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        for element in soup(["script", "style", "meta", "link", "noscript"]):
            element.decompose()

        text = soup.get_text(separator='\n')
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = '\n'.join(lines)
        
        print(f"Successfully scraped content from {url}")
        return text
    except requests.RequestException as e:
        return f"Error: Could not fetch the website. {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

def save_to_file(content, filename):
    """Save the content to a local file."""
    try:
        print(f"Saving content to {filename}...")
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Content saved locally to {filename}")
        return True
    except Exception as e:
        print(f"File Save Error: {e}")
        return False

def store_metadata_in_firestore(url, gcs_path, podcast_gcs_path):
    """Store URL, content path, and podcast path in Firestore."""
    try:
        print("Storing metadata in Firestore...")
        db = firestore.Client()
        doc_ref = db.collection('scraped_urls').document()
        doc_data = {
            'source_url': url,
            'content_gcs_path': gcs_path,
            'podcast_gcs_path': podcast_gcs_path,
            'timestamp': datetime.now(),
            'status': 'completed'
        }
        doc_ref.set(doc_data)
        print("Metadata stored successfully in Firestore.")
        return True, doc_ref.id
    except Exception as e:
        print(f"Firestore Error: {e}")
        return False, str(e)

def generate_conversation(article):
    """Generate podcast conversation from an article."""
    vertexai.init(project="sascha-playground-doit", location="us-central1")
    model = GenerativeModel(
        "gemini-1.5-flash-002",
        system_instruction=[
            "you are an experienced podcast host. Generate engaging conversations based on the content provided."
        ]
    )
    generation_config = GenerationConfig(
        max_output_tokens=8192,
        temperature=0.7,
        top_p=0.95
    )

    responses = model.generate_content([article], generation_config=generation_config)
    print(responses)
    conversation = json.loads(responses.candidates[0].content.parts[0].text)
    print("Generated podcast conversation.")
    return conversation

def save_conversation(conversation):
    """Save the conversation JSON to a file."""
    os.makedirs("./conversation", exist_ok=True)
    output_path = "./conversation/conversation.json"
    with open(output_path, "w") as json_file:
        json.dump(conversation, json_file, indent=4)
    print(f"Conversation saved to {output_path}")

def generate_audio(conversation):
    """Generate podcast audio."""
    os.makedirs("./audio-files", exist_ok=True)
    combined_audio = AudioSegment.empty()

    for index, turn in enumerate(conversation):
        speaker = turn['speaker']
        text = turn['text']
        print(f"Synthesizing audio for: {speaker}: {text[:30]}...")
        # Add TTS synthesis for the speaker here.

    output_file = "podcast.mp3"
    combined_audio.export(output_file, format="mp3")
    print("Podcast audio saved as podcast.mp3")
    return output_file

def main():
    url = "https://developers.googleblog.com/en/gemini-2-0-level-up-your-apps-with-real-time-multimodal-interactions/"
    
    if not is_valid_url(url):
        print("Invalid URL. Please enter a valid URL.")
        return

    # Scrape website content
    content = scrape_website(url)
    if content.startswith("Error:"):
        print(content)
        return

    # Save content locally
    domain = urlparse(url).netloc
    filename = f"{domain}.txt"
    if not save_to_file(content, filename):
        print("Failed to save scraped content.")
        return

    # Upload content to GCS
    success, gcs_path = upload_to_gcs(filename, filename, BUCKET_FOLDER)
    if not success:
        print("Failed to upload content to GCS.")
        return

    # Generate podcast
    conversation = generate_conversation(content)
    save_conversation(conversation)
    podcast_file = generate_audio(conversation)

    # Upload podcast to GCS
    success, podcast_gcs_path = upload_to_gcs(podcast_file, podcast_file, PODCAST_FOLDER)
    if not success:
        print("Failed to upload podcast to GCS.")
        return

    # Store metadata in Firestore
    if not store_metadata_in_firestore(url, gcs_path, podcast_gcs_path):
        print("Failed to store metadata in Firestore.")
        return

    # Clean up local files
    os.remove(filename)
    os.remove(podcast_file)
    print(f"Cleaned up local files: {filename} and {podcast_file}")

if __name__ == "__main__":
    main()
