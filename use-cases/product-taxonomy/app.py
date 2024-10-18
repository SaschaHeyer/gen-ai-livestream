import streamlit as st
import base64
import vertexai
import requests
import time  # Import to measure response time
from vertexai.generative_models import GenerativeModel, Part, SafetySetting

# Initialize the Vertex AI client
def initialize_vertex_ai():
    vertexai.init(project="sascha-playground-doit", location="us-central1")

# Function to generate the content using Vertex AI and retrieve metadata
def generate_content(model_name, text_input, system_instruction):
    model = GenerativeModel(
        model_name,
        system_instruction=[system_instruction]
    )
    
    # Generate content with metadata (stream=False to get full metadata)
    start_time = time.time()  # Start the timer to measure response time
    responses = model.generate_content(
        [text_input],
        generation_config=generation_config,
        safety_settings=safety_settings,
        stream=False,
    )
    end_time = time.time()  # End the timer to measure response time
    
    response_time_ms = (end_time - start_time) * 1000  # Convert time to milliseconds
    return responses, response_time_ms

# Function to fetch taxonomy from a URL
def fetch_taxonomy(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check if the request was successful
        return response.text
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching taxonomy: {e}")
        return None

# Function to calculate costs based on token counts
def calculate_cost(prompt_token_count, candidates_token_count):
    input_cost = (prompt_token_count / 1000) * 0.00001875  # Input cost rate
    output_cost = (candidates_token_count / 1000) * 0.000075  # Output cost rate
    total_cost = input_cost + output_cost
    return input_cost, output_cost, total_cost

# Streamlit widescreen layout
st.set_page_config(layout="wide")

# Streamlit UI components
st.title("DoiT Product Taxonomy Classifier")

st.markdown("""
    Application by [Sascha Heyer](https://www.linkedin.com/in/saschaheyer/)
""")

# Updated product description for the cat toy
text_input = st.text_area("Enter Product Description", value="""Title: Interactive Electric Cat Toy with Motion Sensor, LED Light, and Feather Attachments
Description: Keep your cat entertained and engaged with this motion-activated cat toy. The built-in motion sensor detects when your cat is nearby and automatically activates, making playtime exciting and interactive. The rotating feather attachment stimulates your cat’s hunting instincts, while the LED light adds extra fun during night play. Designed for easy setup and powered by a quiet motor, it ensures your pet stays active in a calm environment. Portable and lightweight, it's perfect for use anywhere in the house, encouraging your cat to stay active and healthy.""")

# Input for taxonomy URL with a default value
taxonomy_url = st.text_input(
    "Enter Taxonomy URL", 
    value="https://www.google.com/basepages/producttype/taxonomy.en-US.txt"
)

# Initialize session state for taxonomy_text
if 'taxonomy_text' not in st.session_state:
    st.session_state.taxonomy_text = None

# Fetch taxonomy from the provided URL
if st.button("Load Taxonomy"):
    st.session_state.taxonomy_text = fetch_taxonomy(taxonomy_url)
    if st.session_state.taxonomy_text:
        st.success("Taxonomy loaded successfully.")

# Always show the taxonomy, even after clicking the "Generate" button
if st.session_state.taxonomy_text:
    st.text_area("Taxonomy Content", value=st.session_state.taxonomy_text, height=300)

# Generation configuration (as hardcoded in the original code)
generation_config = {
    "max_output_tokens": 8192,
    "temperature": 1,
    "top_p": 0.95,
}

# Safety settings
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

# Model selection (assuming the user might want to choose different versions)
model_name = st.selectbox("Choose Model", options=["gemini-1.5-flash-002", "gemini-1.5", "gemini-2"])

# Button to trigger generation
if st.button("Classify product"):
    # Ensure taxonomy_text is loaded or provide a default instruction
    if st.session_state.taxonomy_text is None:
        st.error("Please load the taxonomy before generating content.")
    else:
        system_instruction = f"As a product taxonomy expert based on a predefined product taxonomy you are categorizing products either based on the image and or the product description and potential additional metadata.\n\n{st.session_state.taxonomy_text}"
        
        st.write("Generating content...")

        # Initialize Vertex AI
        initialize_vertex_ai()

        # Generate content and retrieve metadata and response time
        responses, response_time_ms = generate_content(model_name, text_input, system_instruction)

        # Display generated content prominently as "Classified Taxonomy"
        generated_text = responses.candidates[0].content.parts[0].text
        st.subheader("Classified Taxonomy:")
        st.markdown(f"### {generated_text}")

        # Extract metadata
        prompt_token_count = responses.usage_metadata.prompt_token_count
        candidates_token_count = responses.usage_metadata.candidates_token_count
        total_token_count = responses.usage_metadata.total_token_count

        # Calculate cost
        input_cost, output_cost, total_cost = calculate_cost(prompt_token_count, candidates_token_count)

        # Create 3 columns for token info, cost, and response time
        col1, col2, col3 = st.columns(3)

        # Column 1: Token Usage Information
        with col1:
            st.subheader("Token Usage Information:")
            st.write(f"Prompt Token Count: {prompt_token_count}")
            st.write(f"Candidates Token Count: {candidates_token_count}")
            st.write(f"Total Token Count: {total_token_count}")

        # Column 2: Cost Calculation
        with col2:
            st.subheader("Cost Calculation:")
            st.write(f"Input Cost: ${input_cost:.6f}")
            st.write(f"Output Cost: ${output_cost:.6f}")
            st.write(f"Total Cost: ${total_cost:.6f}")

        # Column 3: Response Time
        with col3:
            st.subheader("Response Time:")
            st.write(f"Response Time: {response_time_ms:.2f} ms")
