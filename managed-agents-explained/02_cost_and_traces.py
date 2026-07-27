"""Second pass. Full step traces, the real token floor, and the network default."""
import json, os, time, pathlib, warnings
warnings.filterwarnings("ignore")

from google import genai

OUT = pathlib.Path(__file__).parent / "output"
OUT.mkdir(parents=True, exist_ok=True)
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
BASE = "antigravity-preview-05-2026"


def trace(it):
    """Print EVERY step type, not just function_call."""
    for s in (getattr(it, "steps", None) or []):
        t = getattr(s, "type", "?")
        if t in ("thought",):
            continue
        bits = [t]
        for attr in ("name", "language"):
            v = getattr(s, attr, None)
            if v:
                bits.append(str(v))
        line = "  " + " | ".join(bits)
        args = getattr(s, "arguments", None)
        res = getattr(s, "result", None) or getattr(s, "output", None)
        if args is not None:
            line += "  args=" + str(args)[:150].replace("\n", "\\n")
        if res is not None:
            line += "  -> " + str(res)[:220].replace("\n", "\\n")
        print(line)


def usage(label, it):
    u = it.usage
    print(f"{label}: total={u.total_tokens} in={u.total_input_tokens} "
          f"out={u.total_output_tokens} thought={u.total_thought_tokens} "
          f"cached={getattr(u,'total_cached_tokens',None)}")


# ---- 1. Clean up the stray agent from pass one. ---------------------------
try:
    client.agents.delete(id="Release_Notes")
    print("cleaned up stray agent Release_Notes")
except Exception as e:
    print("cleanup:", str(e)[:100])

# ---- 2. The real token floor on THIS path. --------------------------------
t = time.time()
hello = client.interactions.create(
    agent=BASE, input="Say hello in one word.", environment={"type": "remote"})
usage("\nFLOOR  'Say hello in one word.'", hello)
print("  wall clock %.1fs" % (time.time() - t))
print("  output:", repr(hello.output_text))
(OUT / "floor-hello.json").write_text(json.dumps(hello.model_dump(mode="json"), indent=1, default=str))

# ---- 3. Full trace of a real coding task. ---------------------------------
t = time.time()
code = client.interactions.create(
    agent=BASE,
    input="Write fizz.py that prints fizzbuzz for 1 to 15, run it, and report the exact output.",
    environment={"type": "remote"})
usage("\nTRACE  fizzbuzz", code)
print("  wall clock %.1fs" % (time.time() - t))
print("  --- every step ---")
trace(code)
(OUT / "trace-fizz.json").write_text(json.dumps(code.model_dump(mode="json"), indent=1, default=str))

# ---- 4. Is the sandbox on the network by default? -------------------------
net = client.interactions.create(
    agent=BASE,
    input="Run exactly: curl -sS -m 15 -o /dev/null -w 'HTTP %{http_code}' https://pypi.org/simple/ "
          "Report the raw result including any error, then state plainly whether you have internet.",
    environment={"type": "remote"})
print("\nNETWORK DEFAULT")
trace(net)
print("  ->", (net.output_text or "")[-400:])
(OUT / "network-default.json").write_text(json.dumps(net.model_dump(mode="json"), indent=1, default=str))

# ---- 5. Does the allowlist actually let it through? -----------------------
allow = client.interactions.create(
    agent=BASE,
    input="Run exactly: curl -sS -m 20 -o /dev/null -w 'HTTP %{http_code}' https://pypi.org/simple/ "
          "Report the raw result, then state plainly whether you have internet.",
    environment={"type": "remote", "network": {"allowlist": [{"domain": "pypi.org"}]}})
print("\nNETWORK ALLOWLISTED pypi.org")
trace(allow)
print("  ->", (allow.output_text or "")[-400:])
(OUT / "network-allowlist.json").write_text(json.dumps(allow.model_dump(mode="json"), indent=1, default=str))

print("\nagents now:", [a.id for a in (client.agents.list().agents or [])])
