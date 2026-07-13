"""Deploy the ADK merch-support agent to Agent Runtime, behind the egress
Agent Gateway, with agent identity so Semantic Governance can enforce on it.

Both agent_gateway_config AND identity_type=AGENT_IDENTITY must be set at
create time, per the routing docs. Updating an existing agent does not
retroactively enable SGP.
"""

import vertexai
from google.adk.agents import Agent
from vertexai import agent_engines, types

PROJ = "sascha-playground-doit"
LOC = "us-central1"
GW = f"projects/{PROJ}/locations/{LOC}/agentGateways/merch-egress-gw"
BUCKET = f"gs://{PROJ}-agent-staging"


def issue_refund(order_id: str, amount_eur: float, ship_country: str) -> dict:
    """Issue a refund for a creator merch order.

    Args:
        order_id: the order to refund, e.g. HAM-4471
        amount_eur: refund amount in euros
        ship_country: destination country the order shipped to
    """
    return {
        "status": "refunded",
        "order_id": order_id,
        "amount_eur": amount_eur,
        "ship_country": ship_country,
    }


agent = Agent(
    model="gemini-2.5-flash",
    name="merch_support_agent",
    instruction=(
        "You are the support agent for a creator merch store based in Hamburg. "
        "When a customer asks for a refund, call issue_refund with the order id, "
        "the amount in euros, and the destination country. If a refund is blocked "
        "by policy, explain the reason plainly."
    ),
    tools=[issue_refund],
)

app = agent_engines.AdkApp(agent=agent)
client = vertexai.Client(project=PROJ, location=LOC)

print("Deploying merch_support_agent to Agent Runtime (this builds a container)...")
remote = client.agent_engines.create(
    agent=app,
    config={
        "requirements": [
            "google-cloud-aiplatform[agent_engines,adk]",
            "cloudpickle",
            "pydantic",
        ],
        "staging_bucket": BUCKET,
        "agent_gateway_config": {
            "agent_to_anywhere_config": {"agent_gateway": GW},
        },
        "identity_type": types.IdentityType.AGENT_IDENTITY,
        "env_vars": {
            "GOOGLE_API_PREVENT_AGENT_TOKEN_SHARING_FOR_GCP_SERVICES": "False",
        },
    },
)
print("DEPLOYED:", remote.api_resource.name)
