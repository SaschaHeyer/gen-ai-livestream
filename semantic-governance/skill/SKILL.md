---
name: semantic-governance
description: Use this skill when governing an AI agent's tool calls with a plain-English policy on Google's Gemini Enterprise Agent Platform, using Semantic Governance Policies (SGP). Covers deploying an ADK agent to Agent Runtime behind the Agent Gateway with agent identity, standing up the SGP engine and the VPC network path (PSC endpoint, network attachment, DNS peering), wiring the authz extension and policy, and creating a natural-language constraint that returns ALLOW or DENY on each proposed tool call. Tools, ADK (google-adk), vertexai agent_engines, gcloud network-services / compute / ai, Semantic Governance Policies.
---

# Semantic Governance Skill

Govern an agent's tool calls with one plain-English sentence. Semantic Governance Policies (SGP) sit at the Agent Gateway and evaluate every proposed tool call against your natural-language constraint, returning ALLOW or DENY with a rationale before the tool runs. This skill reproduces, end to end, an ADK agent that gets a real DENY on an over-limit refund and a real ALLOW on an in-limit one.

## Overview

- Build any agent with Google's ADK and deploy it to Agent Runtime.
- Put it behind the Agent Gateway so its model traffic is governed.
- Attach a policy written as a sentence ("Never issue a refund greater than 75 euros.").
- The gateway calls the SGP engine on each `:generateContent`, the engine judges the proposed tool call, and blocks it if it violates the sentence.

> [!IMPORTANT]
> Two settings must both be present AT CREATE time or the agent is silently not governed: `identity_type=AGENT_IDENTITY` and `agent_gateway_config`. Updating an existing agent does NOT retroactively enable SGP, you must deploy fresh with both.

> [!IMPORTANT]
> Use model `gemini-2.5-flash`. Confirm the model actually serves in your project/region with the SDK before deploying.

> [!WARNING]
> The docs' example model `gemini-3.5-flash` returns `404 NOT_FOUND / no access` in a normal project. Symptom, the deployed agent 500s (or, with failOpen true, returns a model 404). Swap to a model you verified serves.

> [!WARNING]
> SGP is Preview. The verdict is itself an LLM call, so it is probabilistic and adds one model round-trip of cost and latency per tool call. It does not support VPC Service Controls. Keep hard-coded checks for money-critical actions and use SGP for fuzzy-intent governance.

---

## Quick Start

Set once. `PROJECT_ID`, `LOCATION=us-central1` (an SGP-supported region), and an application-default login (`gcloud auth application-default login`).

### 1. Build and deploy the ADK agent (behind the gateway)

`demo/deploy_agent.py`, the load-bearing part is the `config` dict.

```python
# pip install "google-cloud-aiplatform[agent_engines,adk]>=1.112"
from google.adk.agents import Agent
from vertexai import agent_engines, types
import vertexai

def issue_refund(order_id: str, amount_eur: float, ship_country: str) -> dict:
    return {"status": "refunded", "order_id": order_id, "amount_eur": amount_eur, "ship_country": ship_country}

agent = Agent(model="gemini-2.5-flash", name="merch_support_agent", tools=[issue_refund],
              instruction="You are support for a Hamburg merch store. Call issue_refund for refund requests.")
app = agent_engines.AdkApp(agent=agent)
client = vertexai.Client(project=PROJECT_ID, location=LOCATION)

remote = client.agent_engines.create(agent=app, config={
    "requirements": ["google-cloud-aiplatform[agent_engines,adk]", "cloudpickle", "pydantic"],
    "staging_bucket": "gs://STAGING_BUCKET",
    "agent_gateway_config": {"agent_to_anywhere_config": {"agent_gateway": GATEWAY_URI}},
    "identity_type": types.IdentityType.AGENT_IDENTITY,
    "env_vars": {"GOOGLE_API_PREVENT_AGENT_TOKEN_SHARING_FOR_GCP_SERVICES": "False"},
})
```

> [!WARNING]
> `env_vars` values must be strings. Passing the docs' boolean `False` raises `TypeError: Unknown value type ... Must be a str or SecretRef`. Use `"False"`.

> [!WARNING]
> The gateway (`GATEWAY_URI`) must exist BEFORE this deploy, because `agent_gateway_config` references it. Create the gateway (step 2) first.

Deploying auto-registers the agent in the Agent Registry as a `projects/.../agents/agentregistry-...` resource. Find that registry name, it is what the policy's `--agent` flag needs (NOT the `reasoningEngines/...` path):

```bash
curl -s -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://agentregistry.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/agents?pageSize=100" \
  | python3 -c "import sys,json;[print(a['name']) for a in json.load(sys.stdin)['agents'] if 'REASONING_ENGINE_ID' in json.dumps(a)]"
```

### 2. Create the egress Agent Gateway

`agent-gateway-egress.yaml`:
```yaml
name: merch-egress-gw
protocols: [MCP]
googleManaged: {governedAccessPath: AGENT_TO_ANYWHERE}
registries: ["//agentregistry.googleapis.com/projects/PROJECT_ID/locations/LOCATION"]
```
```bash
gcloud network-services agent-gateways import merch-egress-gw --source=agent-gateway-egress.yaml --location=LOCATION
```
> [!WARNING]
> The `import` blocks for a while and the CLI may look hung, it is a long provisioning op, the resource still lands. Verify with `... agent-gateways list`.

### 3. Activate the SGP engine

```bash
curl -X PATCH "https://LOCATION-aiplatform.googleapis.com/v1beta1/projects/PROJECT_ID/locations/LOCATION/semanticGovernancePolicyEngine?updateMask=SemanticGovernancePolicyEngine" \
  -H "Authorization: Bearer $(gcloud auth application-default print-access-token)" -H "Content-Type: application/json" -d '{}'
# poll until state: ACTIVE, then save the pscServiceAttachment it returns
```

### 4. Build the private network path to the engine

This is the step the docs bury and it is the one that makes or breaks enforcement.

```bash
# proxy-only subnet (range must NOT overlap 10.128.0.0/9 in an auto-mode network)
gcloud compute networks subnets create sgp-proxy-subnet --network=default --region=LOCATION \
  --range=192.168.100.0/24 --purpose=REGIONAL_MANAGED_PROXY --role=ACTIVE
# network attachment so the gateway can reach into your VPC
gcloud compute network-attachments create sgp-nw-attachment --region=LOCATION --subnets=default --connection-preference=ACCEPT_AUTOMATIC
# static IP + PSC endpoint to the engine's service attachment + DNS record
gcloud compute addresses create sgp-psc-ip --region=LOCATION --subnet=default --purpose=GCE_ENDPOINT
IP=$(gcloud compute addresses describe sgp-psc-ip --region=LOCATION --format="value(address)")
gcloud compute forwarding-rules create sgp-psc-ep --region=LOCATION --network=default --address=sgp-psc-ip --target-service-attachment=PSC_SERVICE_ATTACHMENT
gcloud dns managed-zones create sgp-zone --dns-name="sgp.internal." --visibility=private --networks=default
gcloud dns record-sets create LOCATION.sgp.internal. --zone=sgp-zone --type=A --ttl=300 --rrdatas=$IP
```

### 5. Give the gateway VPC connectivity (the linchpin)

Re-import the gateway WITH a `networkConfig`. Without this the gateway cannot reach the engine, the authz callout fails, and with `failOpen:false` every model call returns `500` with no useful error.

```yaml
name: merch-egress-gw
protocols: [MCP]
googleManaged: {governedAccessPath: AGENT_TO_ANYWHERE}
registries: ["//agentregistry.googleapis.com/projects/PROJECT_ID/locations/LOCATION"]
networkConfig:
  egress: {networkAttachment: projects/PROJECT_ID/regions/LOCATION/networkAttachments/sgp-nw-attachment}
  dnsPeeringConfig:
    domains: ["sgp.internal."]
    targetProject: PROJECT_ID
    targetNetwork: projects/PROJECT_ID/global/networks/default
```
```bash
gcloud network-services agent-gateways import merch-egress-gw --source=agent-gateway-egress.yaml --location=LOCATION
```
> [!WARNING]
> Allow several minutes AFTER this applies before enforcement is live. Symptom of "not live yet", the agent 500s (callout still failing). It flips to real ALLOW/DENY once the network path is up.

### 6. Wire the authz callout, `demo/authz_ext.json` + `demo/authz_policy.json`

```bash
# authz extension points at the engine's DNS hostname
curl -X POST ".../authzExtensions?authzExtensionId=sgp-authz-ext" ... -d @authz_ext.json     # service+authority = LOCATION.sgp.internal, failOpen: false
# authz policy binds it to the gateway on the :generateContent path
curl -X POST ".../authzPolicies?authzPolicyId=sgp-authz-policy" ... -d @authz_policy.json     # action CUSTOM, policyProfile CONTENT_AUTHZ
```

### 7. Create the policy, one sentence

```bash
CLOUDSDK_API_ENDPOINT_OVERRIDES_AIPLATFORM="https://LOCATION-aiplatform.googleapis.com/" \
gcloud beta ai semantic-governance-policies create refund-cap \
  --location=LOCATION --display-name="Refund cap 75 EUR" \
  --agent="projects/PROJECT_ID/locations/LOCATION/agents/agentregistry-..." \
  --natural-language-constraint="Never issue a refund greater than 75 euros."
```
> [!WARNING]
> `--agent` wants the Agent Registry name from step 1, not the `reasoningEngines/...` path. Passing the engine path fails with `SEMANTIC_GOVERNANCE_POLICY_AGENT_INVALID_NAME`.

### 8. Run it, `demo/query_agent.py`

Query the deployed agent. An 89 euro refund is DENIED, a 45 euro one is ALLOWED. Verdicts also land in Cloud Logging under `logName=".../logs/semantic-governance-policy"`.

```
USER: refund the customer their 89 euros
AGENT: I cannot proceed. 89 euros exceeds the refund cap of 75 euros.   # DENY, rationale in the SGP log
USER: refund 45 euros
AGENT: The refund for order HAM-4472 was processed.                     # ALLOW, tool actually ran
```

## Dependencies and Prerequisites

- `google-cloud-aiplatform[agent_engines,adk] >= 1.112`, Python 3.12 (the macOS system Python is too old, use `uv venv --python 3.12`).
- APIs enabled, `aiplatform`, `agentregistry`, `networkservices`, `networksecurity`, `compute`, `dns`.
- SGP Preview access on the project, and an SGP-supported region (us-central1 works).

## Supporting files

- `demo/deploy_agent.py`, the ADK agent + the deploy config that puts it behind the gateway with agent identity.
- `demo/query_agent.py`, drives the agent through the 89/45 euro refunds.
- `demo/authz_ext.json`, `demo/authz_policy.json`, the gateway-to-engine callout wiring.

> [!WARNING]
> Every resource here (gateway, PSC endpoint, network attachment, SGP engine, Agent Runtime deployment) is real billable infrastructure. The PSC endpoint alone is ~$0.025/hr. Tear it all down when done. Agent Runtime itself does not bill when idle.
