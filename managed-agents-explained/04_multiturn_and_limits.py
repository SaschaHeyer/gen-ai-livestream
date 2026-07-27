"""Close the gaps the top-ranking articles cover and we did not.

1. Is Antigravity really the only base agent? (we claim it is)
2. Multi-turn: previous_interaction_id vs environment_id, and are they separable?
3. Is agents.create idempotent?
"""
import os, warnings, json, pathlib
warnings.filterwarnings("ignore")
from google import genai

OUT = pathlib.Path(__file__).parent / "output"
OUT.mkdir(parents=True, exist_ok=True)
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
BASE = "antigravity-preview-05-2026"

# ---- 1. Is there a Deep Research base agent? -------------------------------
print("=== 1. other base agents ===")
for cand in ["deep-research-preview-05-2026", "deep-research", "deep-research-preview"]:
    try:
        r = client.interactions.create(agent=cand, input="Say OK.",
                                       environment={"type": "remote"})
        print(f"  {cand}: ACCEPTED -> {(r.output_text or '')[:60]!r}")
    except Exception as e:
        print(f"  {cand}: rejected -> {str(e)[:130]}")

# ---- 2. Multi-turn, the two different handles ------------------------------
print("\n=== 2. multi-turn ===")
t1 = client.interactions.create(
    agent=BASE,
    input="Write a file /workspace/secret.txt containing exactly: banana-42. Then say DONE.",
    environment={"type": "remote"})
print(f"  turn 1 done. interaction id={t1.id[:24]}...  env={t1.environment_id}")

# 2a. environment only -> filesystem should survive, conversation should NOT
t2 = client.interactions.create(
    agent=BASE,
    input="Without using any tools, tell me what I asked you to do in my previous message. "
          "If you have no previous message, say NO HISTORY.",
    environment=t1.environment_id)
print(f"  2a env-only, history? -> {(t2.output_text or '').strip()[:110]!r}")

# 2b. environment + previous_interaction_id -> both should survive
t3 = client.interactions.create(
    agent=BASE,
    input="Without using any tools, tell me what I asked you to do in my previous message.",
    environment=t1.environment_id,
    previous_interaction_id=t1.id)
print(f"  2b env+prev,  history? -> {(t3.output_text or '').strip()[:110]!r}")

# 2c. filesystem really persisted?
t4 = client.interactions.create(
    agent=BASE, input="Read /workspace/secret.txt and report its exact contents.",
    environment=t1.environment_id)
print(f"  2c filesystem persisted? -> {(t4.output_text or '').strip()[:110]!r}")

# ---- 3. Is agents.create idempotent? ---------------------------------------
print("\n=== 3. agents.create twice ===")
AID = "idempotency-probe"
try:
    client.agents.delete(id=AID)
except Exception:
    pass
a1 = client.agents.create(id=AID, base_agent=BASE, system_instruction="probe")
print(f"  first create : OK, id={a1.id}")
try:
    a2 = client.agents.create(id=AID, base_agent=BASE, system_instruction="probe again")
    print(f"  second create: ACCEPTED (idempotent / overwrite), id={a2.id}")
except Exception as e:
    print(f"  second create: rejected -> {str(e)[:150]}")
client.agents.delete(id=AID)
print("  cleaned up")

json.dump({
    "turn1_env": t1.environment_id,
    "env_only_reply": t2.output_text,
    "env_plus_prev_reply": t3.output_text,
    "filesystem_reply": t4.output_text,
}, open(OUT / "multiturn.json", "w"), indent=1)
print("\nsaved multiturn.json")
