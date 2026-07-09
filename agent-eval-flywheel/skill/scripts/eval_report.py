#!/usr/bin/env python3
"""Run an ADK eval and surface the judge's rationale, which adk eval hides.

`adk eval` prints a scores table but drops the per rubric rationale into a
history JSON you have to dig for. This wrapper runs the eval and prints, for
every case and metric, the score AND the judge's written reason when there is
one. Point it at your own agent and evalset.

Usage:
    python eval_report.py AGENT_DIR EVALSET_JSON --config CONFIG_JSON

Example:
    python eval_report.py ./episode_finder \\
        tests/eval/evalsets/episode_finder.evalset.json \\
        --config tests/eval/eval_config_rubric.json

Requires the same env any adk eval needs, for the AI Studio key path:
    export GOOGLE_GENAI_USE_VERTEXAI=0
    export GOOGLE_API_KEY=...
"""
import argparse
import glob
import json
import os
import subprocess
import sys

_STATUS = {1: "PASSED", 2: "FAILED", 3: "NOT_EVALUATED"}


def _latest_history(agent_dir: str) -> str:
    hist = glob.glob(os.path.join(agent_dir, ".adk", "eval_history", "*.json"))
    if not hist:
        sys.exit("No eval history written, did the eval run fail?")
    return max(hist, key=os.path.getmtime)


def main() -> None:
    ap = argparse.ArgumentParser(description="Run adk eval and show the judge's why.")
    ap.add_argument("agent_dir", help="Path to the agent package dir")
    ap.add_argument("evalset", help="Path to the evalset JSON")
    ap.add_argument("--config", required=True, help="Path to the eval config JSON")
    args = ap.parse_args()

    # adk eval is the real work, we only re-read its history for the rationale.
    proc = subprocess.run(
        ["adk", "eval", args.agent_dir, args.evalset, "--config_file_path", args.config],
        stderr=subprocess.DEVNULL,
    )

    data = json.load(open(_latest_history(args.agent_dir)))
    print("\n=== Eval report, scores and the judge's reasons ===")
    for case in data["eval_case_results"]:
        inv = case["eval_metric_result_per_invocation"][0]
        q = inv["actual_invocation"]["user_content"]["parts"][0]["text"]
        a = inv["actual_invocation"]["final_response"]["parts"][0]["text"]
        print(f"\nQ  {q}\nA  {a}")
        for m in inv["eval_metric_results"]:
            print(f"   {m['metric_name']}: {_STATUS.get(m['eval_status'], m['eval_status'])} "
                  f"score={m['score']} threshold={m['threshold']}")
            for r in (m["details"].get("rubric_scores") or []):
                print(f"      why [{r.get('rubric_id')}] {r.get('score')}: {r.get('rationale', '').strip()}")
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
