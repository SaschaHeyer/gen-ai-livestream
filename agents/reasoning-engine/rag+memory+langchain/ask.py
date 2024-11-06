from vertexai.preview import reasoning_engines

PROJECT_ID = "sascha-playground-doit"
LOCATION = "us-central1"
REASONING_ENGINE_ID = "143358724075945984"

remote_agent = reasoning_engines.ReasoningEngine(
    f"projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{REASONING_ENGINE_ID}")

response = remote_agent.query(
    input="provide me a summary of things you know about me and a list of topics i asked?", 
    config={"configurable": {"session_id": "1001"}})

print(response["output"])
print(response)
