#!/usr/bin/env python3
"""Read a failing eval and let a model propose the instruction fix, you approve.

This is the "it proposes, you approve" step made concrete. It runs the eval,
finds the rubric that failed and the judge's written reason, reads the agent's
current instruction, and asks a model to propose a minimal revised instruction
that fixes the failure. It prints the proposal, it does NOT apply it. You read
it, and if you agree, you paste it into the agent and rerun.

The model that proposes the fix is deliberately NOT the judge that graded it,
same decoupling rule as the flywheel, whatever proposes a fix never grades it.

Usage:
    python propose_fix.py AGENT_DIR EVALSET --config CONFIG_JSON

Requires the same env any adk eval needs, for the AI Studio key path:
    export GOOGLE_GENAI_USE_VERTEXAI=0
    export GOOGLE_API_KEY=...
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

from google import genai

_PROPOSER_MODEL = "gemini-2.5-flash"


def _latest_history(agent_dir):
    hist = glob.glob(os.path.join(agent_dir, ".adk", "eval_history", "*.json"))
    if not hist:
        sys.exit("No eval history written, did the eval run fail?")
    return max(hist, key=os.path.getmtime)


def _read_instruction(agent_dir):
    src = open(os.path.join(agent_dir, "agent.py")).read()
    m = re.search(r"instruction=\(\s*(.*?)\s*\),", src, re.DOTALL)
    return m.group(1).strip() if m else "(could not read instruction)"


def _failures(history):
    out = []
    for case in history["eval_case_results"]:
        inv = case["eval_metric_result_per_invocation"][0]
        q = inv["actual_invocation"]["user_content"]["parts"][0]["text"]
        a = inv["actual_invocation"]["final_response"]["parts"][0]["text"]
        for m in inv["eval_metric_results"]:
            for r in (m["details"].get("rubric_scores") or []):
                if r.get("score", 1.0) < 1.0:
                    out.append({"q": q, "a": a, "rubric": r.get("rubric_id"),
                                "reason": r.get("rationale", "").strip()})
    return out


def main():
    ap = argparse.ArgumentParser(description="Propose an instruction fix from a failing eval.")
    ap.add_argument("agent_dir")
    ap.add_argument("evalset")
    ap.add_argument("--config", required=True)
    args = ap.parse_args()

    subprocess.run(["adk", "eval", args.agent_dir, args.evalset,
                    "--config_file_path", args.config], stderr=subprocess.DEVNULL)
    history = json.load(open(_latest_history(args.agent_dir)))
    fails = _failures(history)
    if not fails:
        print("No failing rubrics, nothing to fix.")
        return

    instruction = _read_instruction(args.agent_dir)
    bullets = "\n".join(
        f"- Q: {f['q']}\n  agent answered: {f['a']}\n  rubric '{f['rubric']}' failed because: {f['reason']}"
        for f in fails)

    prompt = (
        "You are an eval optimizer for an AI agent. Below is the agent's current instruction and the "
        "rubrics its answers failed, with the judge's reason for each. Propose a REVISED instruction "
        "that fixes these failures with the smallest change that works. Do not change unrelated "
        "behavior. Output ONLY the new instruction text, no code, no quotes, no explanation.\n\n"
        f"CURRENT INSTRUCTION:\n{instruction}\n\nFAILURES:\n{bullets}"
    )
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    proposal = client.models.generate_content(model=_PROPOSER_MODEL, contents=prompt).text.strip()

    print("\n=== The judge found these failures ===")
    for f in fails:
        print(f"  [{f['rubric']}] {f['reason']}")
    print("\n=== Proposed instruction (a model wrote this, NOT the judge) ===\n")
    print(proposal)
    print("\nApprove it? If yes, paste it into the agent's instruction and rerun the eval.")


if __name__ == "__main__":
    main()
