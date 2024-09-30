import streamlit as st
import requests
import base64
from PIL import Image
import json

# Define the API endpoint for document extraction
API_ENDPOINT = "https://document-understanding-234439745674.us-central1.run.app/process_pdf"

# The default custom response schema
default_custom_schema = {
    "type": "object",
    "properties": {
        "invoice_number": {"type": "string"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "quantity": {"type": "string"},
                    "total": {"type": "string"}
                },
                "required": ["description", "quantity", "total"]
            }
        }
    }
}

# Function to extract text from PDF or image using the extraction API
def extract_data(file, mime_type, custom_schema=None):
    file.seek(0)  # Ensure the file pointer is at the start
    files = {'file': (file.name, file, mime_type)}
    
    # Include the custom schema if provided
    data = {}
    if custom_schema:
        data['response_schema'] = json.dumps(custom_schema)
    
    response = requests.post(API_ENDPOINT, files=files, data=data)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to extract data: {response.status_code}")
        return None

# Function to display PDF in Streamlit using an iframe
def display_pdf(file, height=400):
    file.seek(0)
    base64_pdf = base64.b64encode(file.read()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="{height}px" style="border: none;"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

# Function to display an image in Streamlit
def display_image(file):
    image = Image.open(file)
    st.image(image, use_column_width=True)

# Streamlit UI
st.set_page_config(layout="wide")
st.title("Document Extraction with AI")
st.write("Upload a PDF or Image file to extract structured information.")

# Create a two-column layout
col1, col2 = st.columns([1, 2])

with col1:
    # File uploader widget for PDF and image files
    uploaded_file = st.file_uploader("Choose a PDF or Image file", type=["pdf", "png", "jpg", "jpeg"])

    # Add checkbox for custom response schema
    use_custom_schema = st.checkbox("Use custom response schema", value=True)
    custom_schema = default_custom_schema

    if use_custom_schema:
        # Multi-line text box to input or edit the custom schema, pre-populated with the default schema
        schema_input = st.text_area("Custom Response Schema (in JSON format)", 
                                    value=json.dumps(default_custom_schema, indent=4), 
                                    height=200)
        
        # Try to load the schema input as JSON
        if schema_input:
            try:
                custom_schema = json.loads(schema_input)
            except json.JSONDecodeError:
                st.error("Invalid JSON format. Please provide a valid JSON schema.")

    if uploaded_file is not None:
        mime_type = "application/pdf" if uploaded_file.type == "application/pdf" else "image/jpeg"

        if st.button("Extract Information"):
            with st.spinner("Extracting information..."):
                extracted_data = extract_data(uploaded_file, mime_type, custom_schema)
                if extracted_data:
                    st.success("Information extracted successfully!")
                    st.write("## Extracted Information")
                    st.json(extracted_data)

with col2:
    if uploaded_file is not None:
        if uploaded_file.type == "application/pdf":
            st.write("## PDF Preview")
            display_pdf(uploaded_file, height=400)
        else:
            st.write("## Image Preview")
            display_image(uploaded_file)

st.write("### GitHub Repository")
st.markdown("[Gen AI Livestream - Document Processing GitHub Repo](https://github.com/SaschaHeyer/gen-ai-livestream/tree/main/document-processing)")

st.write("### Article")
st.markdown("[Multimodal Document Processing on Google Cloud](https://medium.com/google-cloud/multimodal-document-processing-800adca336c7)")

st.write("### Recording")

youtube_url = "https://www.youtube.com/embed/TGwHHU9BqOY"
video_iframe = f"""
<iframe width="640" height="360" src="{youtube_url}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
"""
st.markdown(video_iframe, unsafe_allow_html=True)
