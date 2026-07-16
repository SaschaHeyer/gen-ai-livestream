# Always-on memory agent

Build an agent that remembers across sessions. Three ADK agents over a plain SQLite store, ingest turns files into memories, consolidate links them on a timer, query answers with citations. Multimodal, it reads text, images, and audio.

Honest framing, this is not a new Google capability. Google already ships persistent memory with consolidation as the managed Vertex AI Memory Bank. Build this loop by hand to understand consolidation, use Memory Bank when you need scale and isolation.

## Get the skill

Everything lives in [skill/](skill/), so `npx skills add` carries the code and the sample files with it.

- [skill/SKILL.md](skill/SKILL.md), when to use it, the current model id, the verified quick start, and the sharp edges.
- [skill/scripts/memory_agent.py](skill/scripts/memory_agent.py), the ingest, consolidate, query CLI, point it at your own files.
- [skill/sample-files/](skill/sample-files/), a note, a chat screenshot, and a voice memo to run the quick start against.

Built on Google ADK LlmAgent and Gemini 3.1 Flash Lite. Verified on Python 3.12.
