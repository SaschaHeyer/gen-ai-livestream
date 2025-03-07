import vertexai
from vertexai.preview import reasoning_engines

remote_app = reasoning_engines.ReasoningEngine(
    "projects/234439745674/locations/us-central1/reasoningEngines/4136820140530466816"
)

owner = "SaschaHeyer"
issue_number = "1"
repo = "coding-agent-sample-repository-2"

response = remote_app.query(
    input=f"Analyze and fix the issue #{issue_number} in {owner}/{repo}"
)

print(response)
