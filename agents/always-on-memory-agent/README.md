# Always-on memory agent, tested and compared

A deep dive on an existing always-on memory agent sample, plus an honest head to head with the managed Vertex AI Memory Bank. We did not build the sample, it lives in [Google's generative-ai repo](https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/agents/always-on-memory-agent) and was written by Shubham Saboo. We run it, find the rough edges, and compare.

The short version, the sample is a great teaching tool that uses no vector search (it loads the 50 most recent rows). Memory Bank keeps the scoped vector similarity search. Learn with the sample, reach for Memory Bank when you need real users, isolation, and retrieval that scales.

## Get the skill

Everything is in [skill/](skill/).

- [skill/SKILL.md](skill/SKILL.md), how the sample works, its measured rough edges, and the managed alternative.
- [skill/scripts/memory_bank_quickstart.py](skill/scripts/memory_bank_quickstart.py), a verified Memory Bank create, generate, retrieve utility, point it at your own file.
- [skill/reference.md](skill/reference.md), the full verified head to head.
- [skill/sample-files/](skill/sample-files/), example multimodal inputs.

Built on Google ADK, Gemini 3.1 Flash Lite, and Vertex AI Memory Bank. Verified on Python 3.12.
