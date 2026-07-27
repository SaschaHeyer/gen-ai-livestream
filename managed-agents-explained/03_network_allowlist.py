"""Is the network really open by default, and does the allowlist actually restrict?

This is a security-relevant claim, so it gets its own file and multiple domains.
"""
import json, os, pathlib, warnings
warnings.filterwarnings("ignore")
from google import genai

OUT = pathlib.Path(__file__).parent / "output"
OUT.mkdir(parents=True, exist_ok=True)
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
BASE = "antigravity-preview-05-2026"

PROBE = (
    "Run exactly this bash and report the raw stdout verbatim, no commentary, no advice:\n"
    "for h in pypi.org example.com api.github.com cloudflare.com; do "
    "printf '%s ' $h; curl -sS -m 10 -o /dev/null -w '%{http_code}\\n' https://$h/ "
    "|| echo BLOCKED; done"
)


def run(label, env):
    it = client.interactions.create(agent=BASE, input=PROBE, environment=env)
    print(f"\n===== {label} =====")
    for s in (it.steps or []):
        if getattr(s, "type", "") == "code_execution_result":
            print("  raw result:", str(getattr(s, "result", ""))[:400].replace("\n", " | "))
    print("  says:", (it.output_text or "").strip()[:300])
    return it


a = run("DEFAULT  environment={'type':'remote'}", {"type": "remote"})
b = run("ALLOWLIST pypi.org ONLY",
        {"type": "remote", "network": {"allowlist": [{"domain": "pypi.org"}]}})
c = run("ALLOWLIST empty []",
        {"type": "remote", "network": {"allowlist": []}})

for name, it in [("net-default.json", a), ("net-pypi-only.json", b), ("net-empty.json", c)]:
    (OUT / name).write_text(json.dumps(it.model_dump(mode="json"), indent=1, default=str))
print("\nsaved 3 artifacts")
