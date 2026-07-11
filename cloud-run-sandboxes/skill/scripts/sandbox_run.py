#!/usr/bin/env python3
"""Point this at a Cloud Run service deployed with --sandbox-launcher and run code
inside a sandbox. Two modes.

  # run a local Python file inside the sandbox
  python sandbox_run.py --url https://SERVICE.run.app --file exfil.py

  # let Gemini write the code for a task, then run it in the sandbox
  python sandbox_run.py --url https://SERVICE.run.app --generate "sum these numbers 1 2 3"

Add --allow-egress to permit outbound network for that one run (off by default).
Standard library only, no dependencies.
"""
import argparse
import json
import urllib.request


def post(url, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def main():
    ap = argparse.ArgumentParser(description="Run code inside a Cloud Run sandbox")
    ap.add_argument("--url", required=True, help="Service base URL")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to a Python file to run in the sandbox")
    group.add_argument("--generate", metavar="TASK", help="Let Gemini write the code for TASK, then run it")
    ap.add_argument("--allow-egress", action="store_true", help="Permit outbound network for this run")
    args = ap.parse_args()

    base = args.url.rstrip("/")
    if args.file:
        with open(args.file) as f:
            code = f.read()
        out = post(base + "/run", {"code": code, "allow_egress": args.allow_egress})
    else:
        out = post(base + "/generate", {"prompt": args.generate, "allow_egress": args.allow_egress})

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
