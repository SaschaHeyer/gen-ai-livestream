import os
import subprocess
import sys
import tempfile

from flask import Flask, request, jsonify
from google import genai

app = Flask(__name__)

SANDBOX = "/usr/local/gcp/bin/sandbox"
# The sandbox runs with an EMPTY PATH (env is not inherited), so "python3" is not
# found. Invoke the interpreter by absolute path.
PYTHON = os.path.realpath(sys.executable)
_client = None


def client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def run_in_sandbox(code, allow_egress=False):
    """Write code to a temp file and run it inside a fresh throwaway sandbox."""
    with tempfile.NamedTemporaryFile("w", suffix=".py", dir="/tmp", delete=False) as f:
        f.write(code)
        path = f.name
    cmd = [SANDBOX, "do"]
    if allow_egress:
        cmd.append("--allow-egress")
    cmd += ["--", PYTHON, path]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return {"stdout": proc.stdout, "stderr": proc.stderr, "returncode": proc.returncode}


@app.get("/")
def health():
    return "cloud-run-sandbox-demo ok\n"


@app.post("/run")
def run():
    """Run a code string the caller hands us, inside the sandbox. Deterministic."""
    body = request.get_json(force=True)
    code = body["code"]
    allow = bool(body.get("allow_egress", False))
    return jsonify(run_in_sandbox(code, allow))


@app.post("/generate")
def generate():
    """Let Gemini write the Python for a task, then run it in the sandbox."""
    body = request.get_json(force=True)
    prompt = body["prompt"]
    allow = bool(body.get("allow_egress", False))
    model = body.get("model", "gemini-2.5-flash")

    resp = client().models.generate_content(
        model=model,
        contents=(
            "Write a short self-contained Python 3 script for this task. "
            "Output only the code, no markdown fences, no explanation.\n\nTask: " + prompt
        ),
    )
    code = resp.text.strip()
    if code.startswith("```"):
        code = code.split("```", 2)[1]
        if code.startswith("python"):
            code = code[len("python"):]
        code = code.strip()

    result = run_in_sandbox(code, allow)
    return jsonify({"generated_code": code, **result})
