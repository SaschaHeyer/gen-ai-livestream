---
name: always-on-memory-agent
description: Use this skill when evaluating agent memory options, when running or reviewing the always-on memory agent sample (Google generative-ai repo, by Shubham Saboo), or when deciding between a self-hosted memory loop and the managed Vertex AI Memory Bank. Covers how the sample works and its rough edges, and a verified Memory Bank quickstart. SDKs used, Google ADK, google-genai, vertexai agent engines, Gemini 3.1 Flash Lite.
---

# Always-On Memory Agent Skill

A tested comparison, not a build. It covers an existing always-on memory agent sample and the managed Vertex AI Memory Bank, so your agent can help you run the sample, expect its rough edges, and pick the right option.

> [!IMPORTANT]
> The sample is not ours. It lives in Google's repo at github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/agents/always-on-memory-agent, written by Shubham Saboo. This skill tests it and compares it, it does not reimplement it.

> [!IMPORTANT]
> Model id `gemini-3.1-flash-lite`, GA, not new (announced March 2026, GA on Vertex May 2026). Vertex AI Memory Bank is GA. Neither is a new capability, the point is the honest comparison.

## The sample in one look

- Four ADK `Agent`s, an orchestrator routes to ingest, consolidate, query. Tool calling, not `output_schema`.
- Always-on, an aiohttp API on :8888, an inbox folder watcher, and a consolidation loop every 30 minutes.
- SQLite store with summary, entities, topics, connections, importance per memory.

Run it (from the sample repo):

```bash
pip install -r requirements.txt
export GOOGLE_API_KEY=your_ai_studio_key
python agent.py            # watches ./inbox, serves :8888
curl -X POST localhost:8888/ingest -d '{"text":"Sascha streams Nordlicht Friday"}'
curl "localhost:8888/query?q=when+is+the+stream"
```

## Rough edges, measured when running it

- **Retrieval is a recent-window load, not search.** `read_all_memories` is `SELECT * FROM memories ORDER BY created_at DESC LIMIT 50`. There is no vector search in the sample. Past 50 memories, older ones silently drop out of the query context.

> [!WARNING]
> Symptom, a query stops finding an older fact once the store grows past 50 memories. Cause, the LIMIT 50 recent-window load, there is no similarity retrieval to pull it back.

- **Consolidation is capped at LIMIT 10.** `read_unconsolidated_memories` reads at most 10, so a burst of more than ten new memories only partly consolidates per pass.
- **Per ingest latency 2.4 to 4.7s.** Every ingest routes orchestrator to sub agent to tool and back, measured on 3 files.
- **One shared SQLite file, no per user isolation.** Fine for a personal assistant, not multi user.
- **Thin governance.** A delete endpoint exists, no retention, audit, or scoped access. The repo frames it as a reference implementation.

## The managed alternative, Vertex AI Memory Bank

Same three inputs, run for real during the episode. Memory Bank merged them into fewer, user-scoped memories and retrieved by vector similarity search in 0.7s, versus the sample loading its recent window.

> [!IMPORTANT]
> Memory Bank retrieval is a scoped vector similarity search, and memories are stored first person per `user_id`. This is the core difference from the sample, the sample removed the vector search, Memory Bank keeps it.

[scripts/memory_bank_quickstart.py](scripts/memory_bank_quickstart.py), verified, point it at your own file and question.

```bash
gcloud auth application-default login
python scripts/memory_bank_quickstart.py --project YOUR_PROJECT --file notes.txt \
    --query "what do you know about the project?" --user alice
```

The real calls are `client.agent_engines.create()` (engine create was 4.3s in prep), `generate_memories(direct_contents_source={"events": [...]}, scope=...)`, and `retrieve_memories(similarity_search_params={"search_query": ...})`.

## When to use which

- Learn the mechanics, run something small and personal, or stay local and offline, the sample is a great teaching tool and it works.
- Real users, isolation, retention, and retrieval that scales past a recent window, use managed Memory Bank.

## Supporting files

- [scripts/memory_bank_quickstart.py](scripts/memory_bank_quickstart.py), the verified Memory Bank create, generate, retrieve utility, parameterized.
- [reference.md](reference.md), the full verified head to head, both run on the same inputs.
- [sample-files/](sample-files/), example multimodal inputs (a note, a chat screenshot, a voice memo) to feed either system.

## Dependencies and Prerequisites

- Python 3.12 recommended. `google-adk >= 2.4.0`, `google-genai >= 2.12.1` for the sample, `google-cloud-aiplatform >= 1.161.0` for the Memory Bank quickstart.

> [!WARNING]
> The macOS system python is 3.9 and both ADK and google-genai require `>=3.10`. On 3.9 pip serves a stale ADK 1.x and the API looks broken. Use `uv venv --python 3.12`.

## Documentation Pages

You MUST fetch the matching page before writing code. These hosted docs are the source of truth for parameters, types, and edge cases.

- The sample, https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/agents/always-on-memory-agent
- Memory Bank with ADK, https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/memory-bank/adk-quickstart
- ADK memory concepts, https://google.github.io/adk-docs/sessions/memory/

## From the episode

Video walkthrough, link to follow once the stream is up.
