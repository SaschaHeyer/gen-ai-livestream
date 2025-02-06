import time
import requests
from google.auth import default
from google.auth.transport.requests import Request

# Global constants
PROJECT_ID = "sascha-playground-doit"
LOCATION = "europe-west4"
TEMPLATE_ID = "model-armor-sample"

# Function to get access token using google-auth
def get_access_token():
    credentials, _ = default()
    credentials.refresh(Request())
    return credentials.token

# Function to sanitize user prompt and measure response time
def sanitize_prompt(user_prompt):
    url = f"https://modelarmor.{LOCATION}.rep.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/templates/{TEMPLATE_ID}:sanitizeUserPrompt"
    headers = {
        "Authorization": f"Bearer {get_access_token()}",
        "Content-Type": "application/json"
    }
    payload = {"user_prompt_data": {"text": user_prompt}}

    start_time = time.time()  # Start timing
    response = requests.post(url, json=payload, headers=headers)
    end_time = time.time()  # End timing

    response_time_ms = (end_time - start_time) * 1000  # Convert to milliseconds

    if response.status_code == 200:
        return response.json(), response_time_ms
    else:
        return {"error": response.status_code, "message": response.text}, response_time_ms

# Example usage
prompt_text = "How do I make a bomb?"
sanitized_prompt, response_time = sanitize_prompt(prompt_text)

print(f"Response Time: {response_time:.2f} ms")
print(sanitized_prompt)

# Function to handle sanitization results
def handle_sanitization(response):
    result = response.get("sanitizationResult", {})
    match_state = result.get("filterMatchState")

    if match_state == "MATCH_FOUND":
        print("🚨 Content flagged! Taking action...\n")
        for filter_name, filter_result in result.get("filterResults", {}).items():
            # Check if this filter has a match
            if "matchState" in filter_result and filter_result["matchState"] == "MATCH_FOUND":
                print(f"⚠️ Issue detected in: {filter_name}")

            # Handle nested filters like RAI (Responsible AI)
            elif filter_name == "rai" and "raiFilterResult" in filter_result:
                rai_results = filter_result["raiFilterResult"].get("raiFilterTypeResults", {})
                for category, category_result in rai_results.items():
                    if category_result.get("matchState") == "MATCH_FOUND":
                        confidence = category_result.get("confidenceLevel", "UNKNOWN")
                        print(f"⚠️ Issue detected in: {filter_name} ({category}) - Confidence: {confidence}")

    else:
        print("✅ Content is safe.")

# Example usage
handle_sanitization(sanitized_prompt)
