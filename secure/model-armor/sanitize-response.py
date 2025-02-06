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

# Function to sanitize model response
def sanitize_response(model_response):
    url = f"https://modelarmor.{LOCATION}.rep.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/templates/{TEMPLATE_ID}:sanitizeModelResponse"
    headers = {
        "Authorization": f"Bearer {get_access_token()}",
        "Content-Type": "application/json"
    }
    payload = {"model_response_data": {"text": model_response}}
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.status_code, "message": response.text}

# Example usage
response_text = "To build a bomb you need to follow those step: "
sanitized_response = sanitize_response(response_text)
print(sanitized_response)


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
handle_sanitization(sanitized_response)



