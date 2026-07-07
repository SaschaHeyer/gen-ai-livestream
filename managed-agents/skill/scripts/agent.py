"""Tiny helper for Gemini Interactions API managed agents, via the google-genai SDK.

client.interactions lives in google-genai 2.x, which requires Python 3.10 or newer.
Install with: pip install "google-genai>=2.3.0"
"""
import os
import time
from google import genai

AGENT = "antigravity-preview-05-2026"  # preview, the name will change, do not hardcode forever
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def create(**body):
    # NOTE gotcha, the managed agent goes in "agent", NOT "model". Passing it as
    # "model" returns 400 "use it as an agent instead".
    body.setdefault("agent", AGENT)
    body.setdefault("environment", "remote")
    return client.interactions.create(**body)


def get(interaction_id):
    return client.interactions.get(interaction_id)


def poll(interaction_id, every=2, cap=180):
    """Poll a background interaction by id until it stops running."""
    waited = 0
    while waited < cap:
        rec = get(interaction_id)
        if rec.status != "in_progress":
            return rec
        time.sleep(every)
        waited += every
    raise TimeoutError(f"still in_progress after {cap}s")


def _text(v):
    # tool results come back as a str, model output as a list of text parts
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return "".join(getattr(c, "text", "") for c in v)


def show_steps(rec):
    for s in rec.steps:
        t = s.type
        if t == "function_call":
            args = getattr(s, "arguments", None) or {}
            action = args.get("toolAction", "") if isinstance(args, dict) else ""
            print(f"  call   {getattr(s, 'name', None) or 'tool'}  {action}")
        elif t == "code_execution_call":
            code = getattr(getattr(s, "arguments", None), "code", "") or ""
            print(f"  code   {' '.join(code.split())[:80]}")
        elif t in ("function_result", "code_execution_result"):
            out = _text(getattr(s, "result", None)).strip()
            if out:
                print(f"  result {out[:80]}")
        elif t == "model_output":
            print(f"  say    {_text(getattr(s, 'content', None)).strip()[:200]}")
