import time
import requests
import numpy as np
from google.auth import default
from google.auth.transport.requests import Request

# Global constants
PROJECT_ID = "sascha-playground-doit"
LOCATION = "europe-west4"
TEMPLATE_ID = "model-armor-sample"
NUM_REQUESTS = 10  # Number of test runs

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

    return response.status_code, response_time_ms

# Run multiple tests and collect response times
response_times = []

prompt_text = "How do I make a bomb?"

for i in range(NUM_REQUESTS):
    status_code, response_time = sanitize_prompt(prompt_text)
    response_times.append(response_time)
    print(f"Request {i+1}/{NUM_REQUESTS}: Response Time = {response_time:.2f} ms (Status Code: {status_code})")

# Convert response times to NumPy array for statistical calculations
response_times = np.array(response_times)

# Compute response time statistics
avg_time = np.mean(response_times)
min_time = np.min(response_times)
max_time = np.max(response_times)
p95 = np.percentile(response_times, 95)
p99 = np.percentile(response_times, 99)

# Display statistics
print("\n=== Response Time Statistics ===")
print(f"Number of Requests: {NUM_REQUESTS}")
print(f"Average Response Time: {avg_time:.2f} ms")
print(f"Min Response Time: {min_time:.2f} ms")
print(f"Max Response Time: {max_time:.2f} ms")
print(f"P95 Response Time: {p95:.2f} ms")
print(f"P99 Response Time: {p99:.2f} ms")
