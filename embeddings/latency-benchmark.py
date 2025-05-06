#!pip install --upgrade google-genai
#customer had issue with latencies >1 second this script confirmed there is an issue on the google side with aprox 4% of all embeddings requets are above the mean average of 300ms and reaching peaks of 1.5 seconds. google fixed it within 3 days.

import time
from google import genai
from google.genai.types import EmbedContentConfig

# Initialize the client
client = genai.Client(
    vertexai=True, project='sascha-playground-doit', location='europe-west4'
)

# Define the input texts
texts = [
    "How do I change my address on my driver's license?",
]

# Configuration
config = EmbedContentConfig(
    task_type="RETRIEVAL_DOCUMENT",
    output_dimensionality=768,
    title="Driver's License",
)

# Settings
num_requests = 1000
latency_threshold = 1.0  # seconds

# Logging
latencies = []
above_threshold = []
below_threshold = []

for i in range(num_requests):
    start_time = time.time()

    try:
        response = client.models.embed_content(
            model="text-multilingual-embedding-002",
            contents=texts,
            config=config,
        )
    except Exception as e:
        print(f"[{i}] Request failed: {e}")
        continue

    end_time = time.time()
    latency = end_time - start_time
    latencies.append(latency)

    if latency > latency_threshold:
        above_threshold.append(latency)
        print(f"[{i}] High latency: {latency:.3f} seconds")
    else:
        below_threshold.append(latency)

# Summary
print("\n--- Summary ---")
print(f"Total requests: {len(latencies)}")
print(f"Above {latency_threshold}s: {len(above_threshold)} requests")
print(f"Below {latency_threshold}s: {len(below_threshold)} requests")
print(f"Percentage above threshold: {(len(above_threshold) / len(latencies)) * 100:.2f}%")
print(f"Average latency (all): {sum(latencies)/len(latencies):.3f} seconds")

if below_threshold:
    print(f"Average latency (< {latency_threshold}s): {sum(below_threshold)/len(below_threshold):.3f} seconds")
