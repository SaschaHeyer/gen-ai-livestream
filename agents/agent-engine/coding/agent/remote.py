from vertexai import agent_engines

agent = agent_engines.AgentEngine(
    "projects/234439745674/locations/us-central1/reasoningEngines/8616520783159623680"
)
owner = "SaschaHeyer"
issue_number = "1"
repo = "coding-agent-sample-repository"

response = agent.query(
    input=f"Analyze and fix/implement the issue #{issue_number} in {owner}/{repo}"
)

print(response["output"])
