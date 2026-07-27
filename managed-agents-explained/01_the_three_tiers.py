"""Verify the base -> inline -> managed ladder on the Gemini API path.

Every claim in the article and video traces back to a run of this file.
"""
import json, os, sys, time, pathlib

from google import genai

OUT = pathlib.Path(__file__).parent / "output"
OUT.mkdir(parents=True, exist_ok=True)
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
BASE = "antigravity-preview-05-2026"


def show(label, it):
    """Print the usage + step trace + final text of an interaction."""
    print(f"\n===== {label} =====")
    print("status:", getattr(it, "status", "?"))
    u = getattr(it, "usage", None)
    if u:
        print("tokens: total=%s in=%s out=%s thought=%s" % (
            getattr(u, "total_tokens", "?"), getattr(u, "total_input_tokens", "?"),
            getattr(u, "total_output_tokens", "?"), getattr(u, "total_thought_tokens", "?")))
    print("environment_id:", getattr(it, "environment_id", None))
    for s in (getattr(it, "steps", None) or []):
        t = getattr(s, "type", None)
        n = getattr(s, "name", "")
        if t == "function_call":
            print(f"  [call]   {n}")
        elif t == "function_result":
            print(f"  [result] {n}")
    print("--- output_text ---")
    print((getattr(it, "output_text", "") or "")[:1500])
    return it


def dump(name, obj):
    p = OUT / name
    try:
        p.write_text(json.dumps(obj.model_dump(mode="json"), indent=1, default=str))
    except Exception:
        p.write_text(str(obj))
    print("saved", p.name)


t0 = time.time()

# ---- Rung 1, the base agent. Nothing created, nothing configured. -----------
it1 = client.interactions.create(
    agent=BASE,
    input="Write fizz.py that prints fizzbuzz for 1 to 15, run it, and report the exact output.",
    environment={"type": "remote"},
)
show("RUNG 1  base agent", it1)
dump("rung1-base.json", it1)

# ---- Rung 2, custom inline. Same base agent, behaviour changed per call. ----
it2 = client.interactions.create(
    agent=BASE,
    input="Here is the raw changelog:\n- fix: null deref on session resume\n"
          "- feat: add --thinking-level flag\n- chore: bump google-genai to 2.14.0\n"
          "Write the release notes.",
    system_instruction="You write short, plain release notes for developers. No marketing language.",
    environment={
        "type": "remote",
        "sources": [
            {"type": "inline", "target": ".agents/AGENTS.md",
             "content": "Always group notes under Features, Bug Fixes, Dependencies. Never use adjectives."},
        ],
    },
)
show("RUNG 2  inline custom", it2)
dump("rung2-inline.json", it2)

# ---- Rung 3, save it as a managed agent, then invoke by id. ----------------
AGENT_ID = "release-notes-writer"
try:
    client.agents.delete(id=AGENT_ID)
    print("deleted pre-existing", AGENT_ID)
except Exception as e:
    print("no pre-existing agent:", type(e).__name__)

t_create = time.time()
agent = client.agents.create(
    id=AGENT_ID,
    base_agent=BASE,
    description="Turns a raw changelog into release notes",
    system_instruction="You write short, plain release notes for developers. No marketing language.",
    base_environment={
        "type": "remote",
        "sources": [
            {"type": "inline", "target": ".agents/AGENTS.md",
             "content": "Always group notes under Features, Bug Fixes, Dependencies. Never use adjectives."},
        ],
    },
)
print("\n===== RUNG 3  agents.create =====")
print("created id:", agent.id, "in %.1fs" % (time.time() - t_create))
dump("rung3-agent.json", agent)

it3 = client.interactions.create(
    agent=AGENT_ID,
    input="Here is the raw changelog:\n- fix: null deref on session resume\n"
          "- feat: add --thinking-level flag\n- chore: bump google-genai to 2.14.0\n"
          "Write the release notes.",
    environment={"type": "remote"},
)
show("RUNG 3  invoke by id", it3)
dump("rung3-invoke.json", it3)

# ---- The limits, probed rather than quoted. --------------------------------
print("\n===== LIMITS =====")
for bad_id, why in [("gemini-helper", "reserved prefix"), ("Release_Notes", "uppercase/underscore")]:
    try:
        client.agents.create(id=bad_id, base_agent=BASE, system_instruction="x")
        print(f"  {bad_id}: ACCEPTED (expected reject, {why})")
    except Exception as e:
        print(f"  {bad_id}: rejected -> {str(e)[:160]}")

try:
    lst = client.agents.list()
    ids = [a.id for a in (lst.agents or [])]
    print("  agents.list ->", ids)
except Exception as e:
    print("  agents.list failed:", str(e)[:160])

print("\ntotal wall clock %.1fs" % (time.time() - t0))
