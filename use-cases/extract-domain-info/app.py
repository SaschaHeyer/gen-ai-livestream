import streamlit as st
import requests
from bs4 import BeautifulSoup
import base64
import vertexai
from vertexai.generative_models import GenerativeModel, Part, SafetySetting

# Initialize Vertex AI and model configuration
vertexai.init(project="sascha-playground-doit", location="us-central1")

model = GenerativeModel("gemini-1.5-flash-002")
generation_config = {
    "max_output_tokens": 8192,
    "temperature": 1,
    "top_p": 0.95,
}
safety_settings = [
    SafetySetting(category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                  threshold=SafetySetting.HarmBlockThreshold.OFF),
    SafetySetting(category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                  threshold=SafetySetting.HarmBlockThreshold.OFF),
    SafetySetting(category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                  threshold=SafetySetting.HarmBlockThreshold.OFF),
    SafetySetting(category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
                  threshold=SafetySetting.HarmBlockThreshold.OFF),
]

# Function to calculate costs based on token counts
def calculate_cost(prompt_token_count, candidates_token_count):
    cost_per_1k_chars = 0.0000046875
    total_chars = prompt_token_count + candidates_token_count
    total_cost = (total_chars / 1000) * cost_per_1k_chars
    return total_cost

# Streamlit UI
st.title("Event Information Extractor")
url = st.text_input("Enter a website URL to extract event information:")

if url:
    # Crawl the website
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    text_content = soup.get_text(separator=" ", strip=True)  # Extract clean text

    # Display raw content (optional)
    st.subheader("Raw Text Content")
    st.write(text_content)

    # Generate LLM prompt for extraction
    prompt = f"""Extract event start date, ticket price, event location, and lineup from the following content. Make sure as lineup only include the artist names:\n{text_content}
    
    examples
    
    """

    # Generate content using the LLM
    with st.spinner("Extracting event information..."):
        responses = model.generate_content(
            [prompt],
            generation_config=generation_config,
            safety_settings=safety_settings,
            stream=False,
        )
        
        event_info = responses.candidates[0].content.parts[0].text
        
       # for response in responses:
       #     event_info += response.text

        # Extract metadata
        prompt_token_count = responses.usage_metadata.prompt_token_count
        candidates_token_count = responses.usage_metadata.candidates_token_count
        total_token_count = responses.usage_metadata.total_token_count

        # Calculate cost
        total_cost = calculate_cost(prompt_token_count, candidates_token_count)

    # Display extracted information as Markdown
    st.subheader("Extracted Event Information")
    st.markdown(event_info)

    # Display cost information
    st.subheader("Token Usage and Cost")
    st.write(f"Prompt Tokens: {prompt_token_count}")
    st.write(f"Response Tokens: {candidates_token_count}")
    st.write(f"Total Tokens: {total_token_count}")
    st.write(f"Estimated Cost: ${total_cost:.6f}")

# Function to calculate costs based on token counts
def calculate_cost(prompt_token_count, candidates_token_count):
    cost_per_1k_chars = 0.0000046875  # Cost per 1,000 characters
    total_chars = prompt_token_count + candidates_token_count
    total_cost = (total_chars / 1000) * cost_per_1k_chars
    return total_cost
