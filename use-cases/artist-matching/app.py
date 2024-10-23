import streamlit as st
import vertexai
from vertexai.generative_models import GenerativeModel, Part, SafetySetting

# Initialize Vertex AI
def generate_artist_match(query):
    vertexai.init(project="sascha-playground-doit", location="us-central1")
    model = GenerativeModel(
        "gemini-1.5-flash-002",
        system_instruction=[textsi_1]
    )

    responses = model.generate_content(
        [query],
        generation_config=generation_config,
        safety_settings=safety_settings,
        stream=True,
    )

    generated_text = ""
    for response in responses:
        generated_text += response.text

    return generated_text

# Artist system instruction
textsi_1 = """you are an artist matching service based on a list of artists provided. You suggest the correct naming. Users might use slightly different names; you need to ensure they are exactly as in the artist list.

artists:
The Rolling Stones
The Beatles
Led Zeppelin
Pink Floyd
The Who
The Doors
Queen
Aerosmith
The Eagles
Fleetwood Mac
David Bowie
Jimi Hendrix
Bob Dylan
AC/DC
Guns N\' Roses
The Clash
Nirvana
U2
Bruce Springsteen
The Kinks
The Beach Boys"""

# Configuration for generation
generation_config = {
    "max_output_tokens": 8192,
    "temperature": 0,
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

# Streamlit App
st.title("Artist Name Matching Service")

# Input for user query
user_query = st.text_input("Enter an artist name to match:", "")

# Generate button
if st.button("Match Artist Name"):
    if user_query:
        with st.spinner("Matching artist name..."):
            result = generate_artist_match(user_query)
        st.write("Matched Artist:")
        st.write(result)
    else:
        st.warning("Please enter an artist name.")
