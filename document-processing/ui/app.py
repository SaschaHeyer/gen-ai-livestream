import streamlit as st
import requests
import base64
from PIL import Image

# Define the API endpoint for document extraction
API_ENDPOINT = "https://document-understanding-xgdxnb6fdq-uc.a.run.app/process_pdf"

# Function to extract text from PDF or image using the extraction API
def extract_data(file, mime_type):
    file.seek(0)  # Ensure the file pointer is at the start
    files = {'file': (file.name, file, mime_type)}
    response = requests.post(API_ENDPOINT, files=files)
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

    if uploaded_file is not None:
        mime_type = "application/pdf" if uploaded_file.type == "application/pdf" else "image/jpeg"

        if st.button("Extract Information"):
            with st.spinner("Extracting information..."):
                extracted_data = extract_data(uploaded_file, mime_type)
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
