---
name: always-on-memory-agent
description: Use this skill when building an agent that remembers across sessions, when you need persistent long-term memory that ingests files and consolidates facts on its own, or when deciding between rolling your own memory loop and Google's managed Vertex AI Memory Bank. Covers a three-agent ingest, consolidate, and query loop over SQLite, multimodal ingestion of text, images, and audio, and structured output with Pydantic schemas. SDKs used, Google ADK LlmAgent and InMemoryRunner, google-genai, Gemini 3.1 Flash Lite.
---

# Always-On Memory Agent Skill

Build an agent that turns files into durable memories, connects them on a timer, and answers questions with citations back to the sources. Three ADK LlmAgents over a plain SQLite store, so the memory is something you can read, not a black box.

## Overview

- **Ingest**, extracts standalone memories from text, an image, or audio using Gemini multimodal.
- **Consolidate**, reads all raw memories and writes higher level insights that link two or more sources, recording the source ids.
- **Query**, answers using only stored memories and cites the ids it used.

> [!IMPORTANT]
> Use the model id `gemini-3.1-flash-lite`. Verified working through the AI Studio API key during prep. It is cheap and fast, which is what an always-on background loop needs.

> [!WARNING]
> `gemini-2.5-flash-lite` now returns `404 NOT_FOUND, no longer available to new users`. If your code still references it, switch to `gemini-3.1-flash-lite`.

> [!IMPORTANT]
> This pattern is NOT a new Google capability. Google already ships persistent agent memory WITH consolidation as a fully managed service, Vertex AI Memory Bank (`VertexAiMemoryBankService` in ADK), GA today. Build this loop yourself to understand consolidation or to run something small and personal. For real users, data isolation, and scale, reach for Memory Bank instead. See Documentation Pages below.

---

## Quick Start

Install on Python 3.12 (see Dependencies, the system python is too old).

```bash
export GOOGLE_API_KEY=your_ai_studio_key
export GOOGLE_GENAI_USE_VERTEXAI=0

python scripts/memory_agent.py reset
python scripts/memory_agent.py ingest sample-files/nordlicht-kickoff.md sample-files/nordlicht-chat.png sample-files/nordlicht-memo.wav
python scripts/memory_agent.py consolidate
python scripts/memory_agent.py query "Who is doing the Nordlicht thumbnail and is it finished?"
```

The three agents are plain ADK `LlmAgent`s with a Pydantic `output_schema`, which is what forces structured JSON back instead of prose.

```python
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

ingest_agent = LlmAgent(
    name="ingest",
    model="gemini-3.1-flash-lite",
    instruction="Extract each standalone fact worth remembering, one short sentence each, list the entities.",
    output_schema=IngestResult,   # a pydantic BaseModel
    output_key="ingest",
)
```

> [!WARNING]
> `LlmAgent` with `output_schema` set disables tool calls and agent transfer, the model must answer directly with the schema. That is the intended trade for structured extraction, do not also attach tools to these agents.

Run an agent once and read its structured result from the final event.

```python
async def run_once(agent, parts):
    runner = InMemoryRunner(agent=agent, app_name="memory")
    sess = await runner.session_service.create_session(app_name="memory", user_id="sascha")
    msg = types.Content(role="user", parts=parts)
    async for ev in runner.run_async(user_id="sascha", session_id=sess.id, new_message=msg):
        if ev.is_final_response() and ev.content:
            return json.loads(ev.content.parts[0].text)
```

Multimodal ingest is just the right `Part`, an image or audio file goes in as `inline_data`, Gemini reads it.

```python
from pathlib import Path
part = types.Part(inline_data=types.Blob(mime_type="image/png", data=Path("chat.png").read_bytes()))
```

> [!IMPORTANT]
> During prep this genuinely read a chat screenshot PNG (OCR) and transcribed an audio memo WAV, then the query connected facts from the note, the image, and the audio in one answer. Multimodal ingest is real, not text only.

## Measured behavior and sharp edges

- **Extraction is non-deterministic.** Across prep runs the memory ids shifted and one run wrote the name `Lena` where the source said `Lina`. Do not build logic that assumes stable ids or perfect name fidelity, treat memories as fuzzy and let consolidation and citation carry the weight.
- **Consolidation cost scales with the store.** Every consolidate pass re-reads all raw memories through the model, so both latency and token cost grow as memory grows. On a large store this is where your bill comes from. This sample reads the whole table, for anything real, batch or window it.
- **The timer is not a service.** "Always-on" here means a background loop you supervise. If the process dies, memory silently stops improving and nothing tells you. In production, supervise it or use managed Memory Bank.
- **Audio generation model.** `gemini-3.1-flash-tts` does not exist (404). The sample voice memo was generated with `gemini-2.5-flash-preview-tts`. Ingestion of audio uses `gemini-3.1-flash-lite`, only the optional memo generation uses the TTS model.

## Workflow

1. Point ingest at the user's own files, `python scripts/memory_agent.py ingest <file>...`. It accepts text, images (png, jpg), audio (wav), and PDFs.
2. Run `consolidate` after a batch to link facts across files into insights.
3. Run `query "<question>"`, report the answer plus the cited memory ids back to the user.
4. `reset` clears the store, the SQLite file is `memory.db` in the working directory, override with `MEMORY_DB`.

## Dependencies and Prerequisites

- Python 3.12 recommended. Floors, `google-adk >= 2.4.0`, `google-genai >= 2.12.1`, `pillow >= 10.0.0`.

> [!WARNING]
> The macOS system python is 3.9, and both ADK and google-genai require `>=3.10`. On 3.9 pip silently resolves ADK to a stale 1.x and the LlmAgent API looks broken. Symptom, import or attribute errors on `google.adk.agents`. Fix, `uv venv --python 3.12` and install there.

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python google-adk google-genai pillow
```

## Supporting files

- [scripts/memory_agent.py](scripts/memory_agent.py), the ingest, consolidate, query, reset CLI. Point it at your own files, `python scripts/memory_agent.py ingest ./notes.md ./whiteboard.png`.
- [sample-files/](sample-files/), the frozen reproduction inputs from the episode, a meeting note, a chat screenshot, and a voice memo about a fictional project. Used by the Quick Start commands above.
- [requirements.txt](requirements.txt), pinned floors.

## Documentation Pages

You MUST fetch the matching page below before writing code against Memory Bank or ADK memory. These hosted docs are the source of truth for parameters, types, and edge cases, do not rely solely on the examples above.

- Managed alternative, Memory Bank with ADK, https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/memory-bank/adk-quickstart
- ADK memory concepts, https://google.github.io/adk-docs/sessions/memory/

## From the episode

Video walkthrough, link to follow once the stream is up.
