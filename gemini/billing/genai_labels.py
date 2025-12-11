from google import genai
from google.genai import types

# IMPORTANT: Set your API key either as an environment variable (GOOGLE_API_KEY)
# or directly in the client constructor.
# For example: client = genai.Client(api_key="YOUR_API_KEY")
client = genai.Client(vertexai=True)


try:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Tell me a joke.",
        config=types.GenerateContentConfig(
            labels={"customer": "DoiT", "team": "backend"}
        )
    )
    print(response.text)

except Exception as e:
    print(f"An error occurred: {e}")
    print("Please ensure your GOOGLE_API_KEY is set correctly.")
