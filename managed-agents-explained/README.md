# Gemini Managed Agents, the verification scripts

Start with `00_hello_cat.py` if you just want to see one call work.

Every claim and every number in the article
[Gemini Managed Agents, Explained](https://medium.com/google-cloud) came from one of these five
scripts. They are here so you can re-run them and check, or point them at your own project.

Run against the **Gemini API** (`generativelanguage.googleapis.com`) with an API key, not the
Vertex enterprise path. The two behave differently in ways that matter, which is what script 03
demonstrates.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install google-genai            # 2.14.0 or newer, needs Python 3.10+
export GEMINI_API_KEY=...           # from aistudio.google.com
```

Billing must be enabled on the project. A valid key alone is not enough, requests fail without it.

## The scripts

| Script | What it shows |
| --- | --- |
| `00_hello_cat.py` | The smallest thing that works. One call, the agent invents an ASCII cat, writes the program, runs it, and reports its own stdout. Prints where the tokens went. |
| `01_the_three_tiers.py` | The base agent, a custom agent inline, and the same config saved as a managed agent. Plus reserved-prefix enforcement. |
| `02_cost_and_traces.py` | The token floor for a one-word answer, a full step trace with real stdout, and the sandbox network default. |
| `03_network_allowlist.py` | Four domains under three network configs. The result that surprised me most. |
| `04_multiturn_and_limits.py` | `environment_id` versus `previous_interaction_id`, and whether `agents.create` is idempotent. |
| `05_competitor_agent_to_gcs.py` | The full job: research four products, write a markdown report, upload it to Cloud Storage through a credential transform. |

Run them in order, each is standalone:

```bash
python 01_the_three_tiers.py
```

Raw responses land in `output/` so you can diff your run against the article's numbers.

## Script 05 needs two extra things

It writes to a Cloud Storage bucket, so:

```bash
export GCS_BUCKET=your-bucket-name    # a bucket you can write to
gcloud auth print-access-token        # must return a token for an account with write access
```

The interesting part is that the agent's `curl` carries **no** `Authorization` header. The script
puts the token in the network allowlist's `transform` instead, and the egress proxy attaches it on
the way out, so the credential never enters the prompt, the sandbox, or the model's context.

## Three things worth knowing before you run these

1. **The sandbox has open internet by default**, and `"allowlist": []` does not close it. An empty
   list behaves exactly like no configuration. Script 03 proves both.
2. **You are billed for thinking, not the answer.** "Say hello in one word" bills roughly 447 output
   tokens to return 6. Script 02 measures it.
3. **Read `total_cached_tokens`.** Multi-turn agent loops cache heavily and single calls do not
   cache at all, so a flat cost calculation can overstate a long run by about a third.

## Caveats

Everything here ran on 2026-07-27 against a preview API. `antigravity-preview-05-2026` has a date in
its name for a reason, so if a script fails on the model string, that is the first thing to check.
