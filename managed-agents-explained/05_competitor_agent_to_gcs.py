"""The sophisticated use case: a competitor analysis agent that writes its report to GCS.

Exercises, in one run:
  - google_search + url_context for real research
  - code_execution to write the markdown
  - the network allowlist WITH a credential transform (previously untested)
  - a real artifact landing in a real bucket

Cost is measured at the end at Gemini 3.6 Flash paid rates.
"""
import json, os, subprocess, time, pathlib, warnings
warnings.filterwarnings("ignore")
from google import genai

OUT = pathlib.Path(__file__).parent / "output"
OUT.mkdir(parents=True, exist_ok=True)
BUCKET = os.environ.get("GCS_BUCKET", "your-bucket-name")
OBJECT = "competitor-analysis.md"
IN_RATE, OUT_RATE = 1.50, 7.50   # gemini-3.6-flash, per 1M tokens

token = subprocess.run(
    ["gcloud", "auth", "print-access-token"],
    capture_output=True, text=True, check=True).stdout.strip()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

UPLOAD = (f"https://storage.googleapis.com/upload/storage/v1/b/{BUCKET}/o"
          f"?uploadType=media&name={OBJECT}")

TASK = f"""You are producing a competitor analysis for a developer tools company.

Topic: managed agent / AI agent sandbox platforms. Compare these four:
  1. Google Gemini Managed Agents (the Antigravity agent)
  2. OpenAI's Assistants / code interpreter sandbox
  3. E2B (e2b.dev)
  4. Modal (modal.com)

Steps, in order:
1. Research each one. Use google_search and url_context to find current, factual
   information: what the sandbox is, how it is priced, and who it is aimed at.
2. Write a file at /workspace/{OBJECT} in markdown containing:
   - a one paragraph executive summary
   - a comparison table with columns: Product, Sandbox model, Pricing model, Best for
   - one short section per competitor with a "Strength" and a "Weakness" line
   - a final "Where Gemini Managed Agents win and lose" section, two bullets each
   Be concrete. If you could not verify a pricing number, write "not verified" rather
   than guessing.
3. Upload the finished file with exactly this command, and report the raw response:

   curl -sS -X POST --data-binary @/workspace/{OBJECT} \\
     -H "Content-Type: text/markdown" \\
     "{UPLOAD}"

   Do NOT add an Authorization header yourself. One is attached for you.
4. Report the HTTP result of the upload and the total size of the file you wrote.
"""

print("launching competitor analysis agent...")
t0 = time.time()
it = client.interactions.create(
    agent="antigravity-preview-05-2026",
    input=TASK,
    tools=[{"type": "google_search"}, {"type": "url_context"}, {"type": "code_execution"}],
    environment={
        "type": "remote",
        "network": {
            "allowlist": [
                {"domain": "storage.googleapis.com",
                 "transform": {"Authorization": f"Bearer {token}"}},
                {"domain": "e2b.dev"},
                {"domain": "modal.com"},
                {"domain": "openai.com"},
                {"domain": "ai.google.dev"},
            ]
        },
    },
)
elapsed = time.time() - t0

print(f"\nstatus: {it.status}   wall clock: {elapsed:.1f}s")
print("\n--- steps ---")
for s in (it.steps or []):
    t = getattr(s, "type", "?")
    if t == "thought":
        continue
    line = "  " + t
    for a in ("name", "language"):
        v = getattr(s, a, None)
        if v:
            line += f" | {v}"
    args = getattr(s, "arguments", None)
    res = getattr(s, "result", None) or getattr(s, "output", None)
    if args is not None:
        line += "  args=" + str(args)[:180].replace("\n", "\\n")
    if res is not None:
        line += "  -> " + str(res)[:260].replace("\n", "\\n")
    print(line)

print("\n--- final output ---")
print((it.output_text or "")[:2500])

u = it.usage
billed_out = u.total_output_tokens + u.total_thought_tokens
cost = (u.total_input_tokens * IN_RATE + billed_out * OUT_RATE) / 1_000_000
print("\n===== COST =====")
print(f"  input   {u.total_input_tokens:,}")
print(f"  output  {u.total_output_tokens:,}")
print(f"  thought {u.total_thought_tokens:,}")
print(f"  total   {u.total_tokens:,}")
print(f"  billed as output: {billed_out:,}")
print(f"  COST: ${cost:.4f}   ({elapsed:.0f}s wall clock)")
print(f"  x100 runs: ${cost*100:.2f}   x1000: ${cost*1000:.2f}")

(OUT / "competitor-agent.json").write_text(json.dumps(it.model_dump(mode="json"), indent=1, default=str))
(OUT / "competitor-cost.json").write_text(json.dumps({
    "input": u.total_input_tokens, "output": u.total_output_tokens,
    "thought": u.total_thought_tokens, "total": u.total_tokens,
    "billed_output": billed_out, "cost_usd": round(cost, 6),
    "wall_clock_s": round(elapsed, 1),
    "rates": {"input_per_1m": IN_RATE, "output_per_1m": OUT_RATE, "model": "gemini-3.6-flash"},
}, indent=1))
print("\nsaved artifacts")
