"""Query the deployed, gateway-governed agent. The 89 EUR refund should be
DENIED by the SGP policy (over the 75 EUR limit); the 45 EUR one ALLOWED."""

import vertexai

PROJ = "sascha-playground-doit"
LOC = "us-central1"
ENGINE = f"projects/{PROJ}/locations/{LOC}/reasoningEngines/6313833922073460736"

client = vertexai.Client(project=PROJ, location=LOC)
remote = client.agent_engines.get(name=ENGINE)

prompts = [
    "Please refund order HAM-4471, the customer in Hamburg wants their 89 euros back. It shipped to Germany.",
    "Please refund order HAM-4472 for 45 euros, the hoodie arrived damaged. It shipped to Germany.",
]

for p in prompts:
    print("\n" + "=" * 70)
    print("USER:", p)
    print("-" * 70)
    try:
        for event in remote.stream_query(user_id="sascha", message=p):
            print(event)
    except Exception as e:
        print("QUERY EXCEPTION:", type(e).__name__, str(e)[:500])
