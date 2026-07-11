# Cloud Run Sandboxes

Run untrusted or model-generated code safely inside a Google Cloud Run service. One deploy flag, `--sandbox-launcher`, turns a container into a host for sealed sandboxes that have no credentials, no metadata server, and no network until you allow it per call.

The installable skill and all verified code live in [skill/](skill/).

- [skill/SKILL.md](skill/SKILL.md), the skill, current facts, quick start, and gotchas inline.
- [skill/scripts/sandbox_run.py](skill/scripts/sandbox_run.py), point it at a deployed service and run a file or a Gemini-generated task in the sandbox.
- [skill/scripts/service/](skill/scripts/service/), the deployable Cloud Run service.
- [skill/scripts/exfil.py](skill/scripts/exfil.py) and [skill/scripts/fetch.py](skill/scripts/fetch.py), the isolation and egress reproductions.
- [skill/scripts/adk_agent.py](skill/scripts/adk_agent.py), the ADK `CloudRunSandboxCodeExecutor` one-liner.

Install the skill.

```
npx skills add https://github.com/SaschaHeyer/gen-ai-livestream/tree/main/cloud-run-sandboxes/skill
```
