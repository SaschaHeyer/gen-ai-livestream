import streamlit as st
from google.cloud import storage
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig, Part
from datetime import datetime
import json

# Google Cloud Configuration
PROJECT_ID = "sascha-playground-doit"
BUCKET_NAME = "doit-llm"

# Define the response schema for transcription and speaker diarization
_RESPONSE_SCHEMA_STRUCT = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "speaker": {
                "type": "string",
                "description": "The name or identifier of the speaker (e.g., Speaker A, Speaker B, or a name like Karen)."
            },
            "transcription": {
                "type": "string",
                "description": "The transcription of the audio segment spoken by the speaker."
            },
            "timestamp": {
                "type": "string",
                "description": "The timestamp in HH:MM:SS format where this segment starts."
            }
        },
        "required": ["speaker", "transcription", "timestamp"]
    }
}

# Upload file to Google Cloud Storage
def upload_to_gcs(file, bucket_name, destination_blob_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_file(file)

    # Return both the `gs://` URI and the public URL
    gs_uri = f"gs://{bucket_name}/{destination_blob_name}"
    public_url = f"https://storage.cloud.google.com/{bucket_name}/{destination_blob_name}"
    return gs_uri, public_url

# Call Gemini model with controlled JSON schema
@st.cache_data
def process_audio_with_gemini(gs_uri):
    vertexai.init(project=PROJECT_ID, location="us-central1")
    model = GenerativeModel("gemini-1.5-pro-002")

    prompt = """
    Generate audio diarization for this audio file. 
    - Use JSON format for the output, with the following keys: "speaker", "transcription", "timestamp". 
    - If you can infer the speaker, please do, only use first name. 
    - If not, use speaker A, speaker B
    """

    audio_file = Part.from_uri(gs_uri, mime_type="audio/mpeg")

    generation_config = GenerationConfig(
        audio_timestamp=True,
        temperature=1.0,
        max_output_tokens=8192,
        response_mime_type="application/json",
        response_schema=_RESPONSE_SCHEMA_STRUCT
    )

    response = model.generate_content(
        [audio_file, prompt],
        generation_config=generation_config,
        stream=False
    )

    return response.candidates[0].content.parts[0].text

# Convert HH:MM:SS to seconds
def timestamp_to_seconds(timestamp):
    try:
        time_obj = datetime.strptime(timestamp, "%H:%M:%S")
        return time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second
    except ValueError:
        time_obj = datetime.strptime(timestamp, "%M:%S")
        return time_obj.minute * 60 + time_obj.second

# Streamlit UI
st.title("Speech to Text with Gemini")
st.subheader("+ Speaker Detection and Timestamps")

# Session state for file paths and processing results
if "gs_uri" not in st.session_state:
    st.session_state["gs_uri"] = None
if "public_url" not in st.session_state:
    st.session_state["public_url"] = None
if "transcription_output" not in st.session_state:
    st.session_state["transcription_output"] = None

# File upload option
uploaded_file = st.file_uploader("Upload an audio file (MP3)", type=["mp3"])

# Manual GCS file path input
gcs_path = st.text_input("Or enter a Google Cloud Storage path (gs://...)", "")

# Handle file upload
if uploaded_file:
    st.write("Uploading file to Google Cloud Storage...")
    blob_name = f"uploads/{uploaded_file.name}"
    gs_uri, public_url = upload_to_gcs(uploaded_file, BUCKET_NAME, blob_name)
    st.session_state["gs_uri"] = gs_uri
    st.session_state["public_url"] = public_url
    st.success(f"File uploaded successfully!")

# Handle manual GCS path input
elif gcs_path.startswith("gs://"):
    st.session_state["gs_uri"] = gcs_path
    st.session_state["public_url"] = None  # No public URL for existing GCS files
    st.success(f"Using existing GCS file: {gcs_path}")

# Process audio if a valid GCS URI is available
if st.session_state["gs_uri"] and not st.session_state["transcription_output"]:
    st.write("Processing audio with Gemini...")
    with st.spinner("Generating transcript and speaker diarization..."):
        try:
            output = process_audio_with_gemini(st.session_state["gs_uri"])
            st.session_state["transcription_output"] = output
            st.success("Processing complete!")
        except Exception as e:
            st.error(f"Error processing the audio: {e}")

# Display transcription and playback controls
if st.session_state["transcription_output"]:
    st.header("Transcription")
    try:
        sections = json.loads(st.session_state["transcription_output"])  # Safely parse JSON
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse JSON response: {e}")
        st.text("Full response below:")
        st.text_area("Malformed JSON", st.session_state["transcription_output"], height=300)
        sections = []
    for idx, section in enumerate(sections):
        st.write(f"**[{section['timestamp']}] {section['speaker']}**: {section['transcription']}")
        if st.button(f"Play from {section['timestamp']}", key=f"{section['timestamp']}_{idx}"):
            start_time = timestamp_to_seconds(section["timestamp"])
            # Use public URL if available, otherwise just display the timestamp
            if st.session_state["public_url"]:
                st.audio(st.session_state["public_url"], start_time=start_time)
            else:
                st.warning("Playback is only available for uploaded files.")
