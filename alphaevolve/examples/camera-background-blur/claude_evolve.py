#!/usr/bin/env python3
"""blurlab Claude Code runner. Optimizes the same seed against the same
evaluator as evolve.py, so the two results are comparable.

The point of this file is a fair head-to-head. AlphaEvolve and Claude Code
get the identical seed (seed.swift), the identical objective (evaluate.py,
same SSIM gate), the identical clip and goldens, the identical problem
statement (problem.py), and the same candidate budget. The only thing that
differs is who writes the candidates.

Two modes, they answer different questions.

  blind    Same information channel as AlphaEvolve. Claude runs with no
           tools in an empty directory, sees only the problem statement,
           the current best program's source, and the scalar scores of
           every candidate so far, and must reply with one Swift file.
           This is the apples-to-apples comparison.

  agentic  How a developer actually uses Claude Code. Claude gets a
           sandbox copy of the harness (bench, evaluator, clip, goldens,
           seed) and may compile and score its own candidates before
           answering. AlphaEvolve's winner and this repo's README are
           deliberately kept out of the sandbox.

Usage.

    python3 claude_evolve.py                       # blind, 10 candidates
    python3 claude_evolve.py --budget 20
    python3 claude_evolve.py --mode agentic --budget 10
    python3 claude_evolve.py --model sonnet --session fresh

Every run writes runs/<mode>-<model>-<timestamp>/ containing the prompt and
raw CLI response for each iteration, every candidate's source, a scores
JSONL, and a summary.json. The winner is copied to claude_best_program.swift
next to this file.

Auth note. This shells out to the `claude` CLI. A logged-in CLI works, and
so does ANTHROPIC_API_KEY. A nested call from inside a running Claude Code
session may fail to refresh its OAuth token, in which case export an API
key first.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from evaluate import FAILED_SCORE, SEED, ensure_goldens, evaluate
from problem import PROBLEM

LAB = Path(__file__).resolve().parent
RUNS = LAB / "runs"

PRIMARY_METRIC = "speedup"
CLI_TIMEOUT = 3600

# Reply contract for blind mode. The model has no tools and no files, so the
# whole exchange is text in, one Swift file out.
BLIND_SYSTEM = (
    "You are the mutation operator inside an evolutionary code-optimization "
    "loop. You will be shown a program and the measured scores of every "
    "candidate tried so far, and you propose the next candidate. Reply with "
    "exactly one complete Swift file inside a single ```swift fence, and no "
    "text outside the fence. The file must be self-contained and compile on "
    "its own, imports included."
)

AGENTIC_SYSTEM = (
    "You are optimizing a performance-critical Swift function. You have the "
    "real benchmark harness, so measure, do not guess. Never weaken the "
    "quality gate, never edit the evaluator, the bench harness, the clip, or "
    "the goldens, and do not look for the answer outside your working "
    "directory. Your score is what the unmodified evaluator reports."
)

FENCE = re.compile(r"```(?:swift)?[ \t]*\n(.*?)```", re.S)

# Dropped into the agentic sandbox as evaluate.py. Identical behaviour to the
# real evaluator, it just records every call so the budget is auditable.
EVAL_SHIM = '''#!/usr/bin/env python3
"""Objective function. Usage, python3 evaluate.py candidate.swift"""

import json
import sys
import time
from pathlib import Path

import blurlab_eval

source = Path(sys.argv[1]) if len(sys.argv) > 1 else blurlab_eval.SEED
scores = blurlab_eval.evaluate(source.read_text())
with (Path(__file__).parent / "evals.log").open("a") as handle:
    handle.write(json.dumps({"at": time.time(), "file": source.name,
                             "scores": scores}) + "\\n")
print(json.dumps(scores, indent=2))
'''


# --- prompts ---------------------------------------------------------------

def history_table(history):
    """The scalar feedback channel, the same numbers AlphaEvolve gets back."""
    rows = ["| candidate | speedup | ssim | verdict |",
            "|---|---|---|---|"]
    for entry in history:
        speedup = entry["scores"][PRIMARY_METRIC]
        shown = "rejected" if speedup == FAILED_SCORE else f"{speedup:.3f}"
        rows.append(f"| {entry['label']} | {shown} | "
                    f"{entry['scores'].get('ssim', 0):.5f} | {entry['verdict']} |")
    return "\n".join(rows)


def blind_prompt(iteration, budget, history, parent_code, parent_label, last):
    """One turn of the blind loop."""
    parts = [
        "## The problem", "", PROBLEM, "",
        "## How you are scored", "",
        "An evaluator on this machine compiles your file with `swiftc -O`, runs "
        "it over a fixed 60-frame 1080p clip, and returns two numbers. "
        "`speedup` is the seed's median milliseconds per frame divided by "
        "yours, higher is better. `ssim` is mean structural similarity against "
        "the seed's own output on the same clip. Below SSIM 0.98 mean or 0.95 "
        "on the worst single frame the candidate is rejected outright, whatever "
        "its speed. You never see a rendered frame, only these numbers.", "",
        f"## Budget", "",
        f"Candidate {iteration} of {budget}.", "",
        "## Results so far", "", history_table(history), "",
    ]
    if last and last["verdict"] != "ok":
        parts += [f"Your previous candidate was {last['verdict']}. "
                  f"{last['insight']}", ""]
    parts += [
        f"## The program to improve ({parent_label}, the best scoring so far)",
        "", "```swift", parent_code.rstrip(), "```", "",
        "## Your turn", "",
        "Propose the next candidate. Reply with the complete Swift file in one "
        "```swift fence and nothing else.",
    ]
    return "\n".join(parts)


def agentic_task(budget):
    return "\n".join([
        "# Task", "", PROBLEM, "",
        "## Your working directory", "",
        "- `candidate.swift` is the program you edit. It starts as an exact "
        "copy of the seed.",
        "- `seed.swift` is the original, keep it for reference, do not edit it.",
        "- `bench.swift` is the benchmark harness. Read it to understand the "
        "measurement, do not edit it.",
        "- `evaluate.py` is the objective function. Run it, do not edit it.",
        "- `clip.mov` and `goldens/` are the fixed test data. Do not touch them.",
        "", "## How to measure", "", "```bash",
        "python3 evaluate.py candidate.swift", "```", "",
        "It prints `{\"speedup\": ..., \"ssim\": ...}`. A speedup of -1e12 means "
        "the candidate failed to compile or fell below the SSIM gate. One "
        "evaluation takes roughly 15 seconds.", "",
        f"You may run the evaluator at most {budget} times. Every call is "
        "counted and the count is part of the result, so spend them "
        "deliberately.", "",
        "## Done", "",
        "Leave your best-scoring version in `candidate.swift`. It will be "
        "re-scored by the unmodified evaluator, and that number is your "
        "result. If nothing you tried beat the seed, leave the seed.",
    ])


# --- the CLI ---------------------------------------------------------------

def run_claude(prompt, *, model, cwd, system, session_id=None,
               allowed_tools=None, log_dir=None, tag=""):
    """One `claude -p` call. Returns (text, meta)."""
    cmd = ["claude", "-p", "--output-format", "json", "--model", model,
           "--append-system-prompt", system]
    if session_id:
        cmd += ["--resume", session_id]
    if allowed_tools:
        cmd += ["--allowed-tools", *allowed_tools]
    else:
        # Blind mode. No tools at all, the prompt is the whole world.
        cmd += ["--disallowed-tools", "Bash", "Read", "Write", "Edit",
                "Glob", "Grep", "WebFetch", "WebSearch", "Task",
                "NotebookEdit", "TodoWrite"]
    started = time.time()
    proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                          cwd=str(cwd), timeout=CLI_TIMEOUT)
    elapsed = time.time() - started
    if log_dir:
        (log_dir / f"{tag}prompt.md").write_text(prompt)
        (log_dir / f"{tag}response.json").write_text(proc.stdout or "")
        if proc.stderr:
            (log_dir / f"{tag}stderr.txt").write_text(proc.stderr)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"the claude CLI returned no JSON\n"
                           f"stdout {proc.stdout[-500:]}\n"
                           f"stderr {proc.stderr[-500:]}")
    if data.get("is_error"):
        raise RuntimeError(f"the claude CLI failed, {data.get('result')}")
    meta = {
        "session_id": data.get("session_id"),
        "model": next(iter(data.get("modelUsage", {})), model),
        "cost_usd": data.get("total_cost_usd"),
        "num_turns": data.get("num_turns"),
        "cli_seconds": round(elapsed, 1),
        "output_tokens": data.get("usage", {}).get("output_tokens"),
    }
    return data.get("result", ""), meta


def extract_swift(text):
    """Pull the candidate out of the reply, tolerating a stray fence."""
    blocks = FENCE.findall(text or "")
    good = [b for b in blocks
            if "class EvolvedBlurKernel" in b and "func process(" in b]
    if good:
        return max(good, key=len)
    if "class EvolvedBlurKernel" in (text or "") and "func process(" in text:
        return text  # answered without a fence
    return None


# --- scoring ---------------------------------------------------------------

def verdict_for(scores, code):
    """Turn the evaluator's numbers into the insight string the loop feeds back."""
    if code is None:
        return "unusable", ("The reply contained no complete Swift file with "
                            "class EvolvedBlurKernel and its process method.")
    if scores[PRIMARY_METRIC] != FAILED_SCORE:
        return "ok", ""
    if scores.get("ssim", 0) > 0:
        return "rejected, ssim gate", (
            f"It compiled and ran, but its output differs visibly from the "
            f"reference (ssim {scores['ssim']:.5f}, floor 0.98). The kernel has "
            f"to produce the same image, only faster.")
    return "rejected, compile or crash", (
        "It did not compile with swiftc -O, or it crashed while rendering. "
        "Check the required class name, the exact process signature, and that "
        "every API you used exists on macOS.")


def record(history, label, code, scores, meta, run_dir, source=None):
    kind, insight = verdict_for(scores, code)
    entry = {"label": label, "scores": scores, "verdict": kind,
             "insight": insight, "meta": meta, "source": source}
    history.append(entry)
    with (run_dir / "scores.jsonl").open("a") as handle:
        handle.write(json.dumps(entry) + "\n")
    speedup = scores[PRIMARY_METRIC]
    shown = "rejected" if speedup == FAILED_SCORE else f"{speedup:.3f}x"
    print(f"  {label}, speedup {shown}, ssim {scores.get('ssim', 0):.5f}"
          f"{', ' + kind if kind != 'ok' else ''}", flush=True)
    return entry


# --- modes -----------------------------------------------------------------

def run_blind(args, run_dir, baseline, seed_code):
    history = []
    record(history, "seed", seed_code, baseline, {}, run_dir)
    best_code, best_score, best_label = seed_code, baseline[PRIMARY_METRIC], "seed"
    session_id = None
    last = None

    with tempfile.TemporaryDirectory(prefix="blurlab-blind-") as empty:
        for i in range(1, args.budget + 1):
            prompt = blind_prompt(i, args.budget, history, best_code,
                                  best_label, last)
            print(f"candidate {i}/{args.budget}", flush=True)
            try:
                text, meta = run_claude(
                    prompt, model=args.model, cwd=empty, system=BLIND_SYSTEM,
                    session_id=session_id if args.session == "continue" else None,
                    log_dir=run_dir, tag=f"cand{i:02d}-")
            except RuntimeError as error:
                print(f"  {error}", file=sys.stderr)
                break
            session_id = meta["session_id"] or session_id
            code = extract_swift(text)
            if code:
                (run_dir / f"cand{i:02d}.swift").write_text(code)
                scores = evaluate(code)
            else:
                scores = dict(speedup=FAILED_SCORE, ssim=0.0)
            last = record(history, f"{i}", code, scores, meta, run_dir)
            if code and scores[PRIMARY_METRIC] > best_score:
                best_code, best_score, best_label = code, scores[PRIMARY_METRIC], f"candidate {i}"
    return history, best_code, best_score


def make_sandbox(run_dir, budget):
    """A working copy of the harness with nothing in it that leaks the answer.

    No best_program.swift, no claude_best_program.swift, no README.md, no
    evolve.py, no runs/. The agent can measure everything and look up nothing.
    """
    sandbox = run_dir / "sandbox"
    sandbox.mkdir()
    for name in ("bench.swift", "seed.swift", "clip.mov"):
        shutil.copy2(LAB / name, sandbox / name)
    shutil.copytree(LAB / "goldens", sandbox / "goldens")
    shutil.copy2(LAB / "seed.swift", sandbox / "candidate.swift")
    # The real evaluator, behind a shim that counts how many times it ran.
    shutil.copy2(LAB / "evaluate.py", sandbox / "blurlab_eval.py")
    (sandbox / "evaluate.py").write_text(EVAL_SHIM)
    (sandbox / "TASK.md").write_text(agentic_task(budget))
    return sandbox


def run_agentic(args, run_dir, baseline, seed_code):
    """One Claude Code session with the harness in a sandbox."""
    history = []
    record(history, "seed", seed_code, baseline, {}, run_dir)
    sandbox = make_sandbox(run_dir, args.budget)

    prompt = ("Read TASK.md in this directory and carry it out. When you are "
              "finished, report the best speedup you measured and what you "
              "changed to get it.")
    text, meta = run_claude(
        prompt, model=args.model, cwd=sandbox, system=AGENTIC_SYSTEM,
        allowed_tools=["Bash(python3 evaluate.py*)", "Read", "Write", "Edit",
                       "Glob", "Grep"],
        log_dir=run_dir, tag="agentic-")
    (run_dir / "agentic-report.md").write_text(text or "")

    code = (sandbox / "candidate.swift").read_text()
    (run_dir / "cand-agentic.swift").write_text(code)
    # The official number, the unmodified evaluator on the untouched harness.
    scores = evaluate(code)
    meta["self_evaluations"] = sum(
        1 for _ in (sandbox / "evals.log").open()) if (sandbox / "evals.log").exists() else None
    record(history, "agentic final", code, scores, meta, run_dir)
    return history, code, scores[PRIMARY_METRIC]


# --- external generator ----------------------------------------------------

# Same loop, same prompts, but the candidate is written by something this
# script does not launch itself (a subagent, a colleague, another vendor's
# model). Three steps, driven from the outside.
#
#   python3 claude_evolve.py --mode external --step init
#   python3 claude_evolve.py --mode external --step emit   --run-dir <dir>
#   python3 claude_evolve.py --mode external --step sandbox --run-dir <dir>
#   python3 claude_evolve.py --mode external --step submit --run-dir <dir> \
#       --candidate reply.swift
#
# State lives entirely in the run directory, so the loop survives being
# picked up and put down between steps.

def load_history(run_dir):
    path = run_dir / "scores.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def source_of(run_dir, entry):
    source = entry.get("source")
    if not source:
        return None
    candidate = Path(source)
    return candidate if candidate.is_absolute() else run_dir / candidate


def best_of(run_dir, history):
    """The parent for the next prompt, the highest scoring program so far."""
    scored = [e for e in history if e["scores"][PRIMARY_METRIC] != FAILED_SCORE]
    best = max(scored, key=lambda e: e["scores"][PRIMARY_METRIC])
    path = source_of(run_dir, best)
    label = "seed" if best["label"] == "seed" else f"candidate {best['label']}"
    return path.read_text(), label


def external_step(args):
    if args.step == "init":
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        run_dir = RUNS / f"external-{args.model}-{stamp}"
        run_dir.mkdir(parents=True)
        ensure_goldens()
        seed_code = SEED.read_text()
        baseline = evaluate(seed_code)
        if baseline[PRIMARY_METRIC] < 0:
            sys.exit("the seed fails its own gate, fix the harness first")
        record([], "seed", seed_code, baseline, {"generator": args.model},
               run_dir, source=str(SEED))
        (run_dir / "config.json").write_text(json.dumps(
            {"mode": "external", "generator": args.model,
             "budget": args.budget,
             "out_name": args.out_name}, indent=2))
        print(run_dir)
        return

    run_dir = Path(args.run_dir).resolve()
    history = load_history(run_dir)
    if not history:
        sys.exit(f"no scores.jsonl in {run_dir}, run --step init first")
    budget = json.loads((run_dir / "config.json").read_text())["budget"]
    done = [e for e in history if e["label"] != "seed"]

    if args.step == "sandbox":
        # The agentic setting, driven from outside. Same sandbox the built-in
        # agentic mode builds, for a generator this script does not launch.
        print(make_sandbox(run_dir, budget))
        return

    if args.step == "emit":
        iteration = len(done) + 1
        if iteration > budget:
            sys.exit(f"budget of {budget} candidates is already spent")
        parent_code, parent_label = best_of(run_dir, history)
        last = done[-1] if done else None
        prompt = blind_prompt(iteration, budget, history, parent_code,
                              parent_label, last)
        (run_dir / f"cand{iteration:02d}-prompt.md").write_text(prompt)
        print(prompt)
        return

    # submit
    iteration = len(done) + 1
    reply = Path(args.candidate).read_text()
    code = extract_swift(reply)
    stored = run_dir / f"cand{iteration:02d}.swift"
    if code:
        stored.write_text(code)
        scores = evaluate(code)
    else:
        scores = dict(speedup=FAILED_SCORE, ssim=0.0)
    record(history, str(iteration), code, scores, {"generator": args.model},
           run_dir, source=stored.name if code else None)
    best_code, best_label = best_of(run_dir, load_history(run_dir))
    print(f"best so far, {best_label}")
    if best_label != "seed":
        config = json.loads((run_dir / "config.json").read_text())
        out = LAB / config.get("out_name", "claude_best_program.swift")
        out.write_text(best_code)
        print(f"winner written to {out.name}")


# --- main ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("blind", "agentic", "external"),
                        default="blind")
    parser.add_argument("--step",
                        choices=("init", "emit", "sandbox", "submit"),
                        help="external mode only")
    parser.add_argument("--run-dir", help="external mode, the run to continue")
    parser.add_argument("--candidate",
                        help="external mode, the file holding the reply")
    parser.add_argument("--out-name", default="claude_best_program.swift",
                        help="external mode, filename for this run's winner. "
                             "Give separate runs separate names or the second "
                             "overwrites the first")
    parser.add_argument("--budget", type=int, default=10,
                        help="candidates (blind) or evaluator calls (agentic)")
    parser.add_argument("--model", default="opus",
                        help="an alias like opus or sonnet, or a full model id")
    parser.add_argument("--session", choices=("continue", "fresh"),
                        default="continue",
                        help="blind mode, keep one conversation across "
                             "candidates or start clean every time")
    parser.add_argument("--dry-run", action="store_true",
                        help="score the seed, print the first prompt, and stop "
                             "without calling the CLI")
    args = parser.parse_args()

    if args.mode == "external":
        if not args.step:
            parser.error("external mode needs --step init, emit, or submit")
        if args.step != "init" and not args.run_dir:
            parser.error("--step emit and submit need --run-dir")
        if args.step == "submit" and not args.candidate:
            parser.error("--step submit needs --candidate")
        return external_step(args)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = RUNS / f"{args.mode}-{args.model}-{stamp}"
    run_dir.mkdir(parents=True)
    print(f"run directory {run_dir}")

    ensure_goldens()
    seed_code = SEED.read_text()
    baseline = evaluate(seed_code)
    print(f"seed scores {baseline}")
    if baseline[PRIMARY_METRIC] < 0:
        sys.exit("the seed fails its own gate, fix the harness before running")

    if args.dry_run:
        preview = (agentic_task(args.budget) if args.mode == "agentic" else
                   blind_prompt(1, args.budget,
                                [{"label": "seed", "scores": baseline,
                                  "verdict": "ok", "insight": ""}],
                                seed_code, "seed", None))
        (run_dir / "dry-run-prompt.md").write_text(preview)
        print(preview)
        return

    runner = run_blind if args.mode == "blind" else run_agentic
    history, best_code, best_score = runner(args, run_dir, baseline, seed_code)

    summary = {
        "mode": args.mode,
        "model": args.model,
        "budget": args.budget,
        "session": args.session,
        "seed_scores": baseline,
        "baseline_ms_per_frame": json.loads(
            (LAB / "goldens" / "manifest.json").read_text())["msPerFrame"],
        "best_speedup": best_score,
        "candidates": [
            {k: entry[k] for k in ("label", "scores", "verdict")}
            for entry in history
        ],
        "cost_usd": round(sum(e["meta"].get("cost_usd") or 0
                              for e in history), 4),
        "wall_clock_seconds": round(sum(e["meta"].get("cli_seconds") or 0
                                        for e in history), 1),
        "finished": datetime.now(timezone.utc).isoformat(),
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    if best_score > baseline[PRIMARY_METRIC]:
        out = LAB / "claude_best_program.swift"
        out.write_text(best_code)
        print(f"best speedup {best_score:.3f}x, program written to {out}")
    else:
        print("nothing beat the seed, claude_best_program.swift left alone")
    print(f"summary {run_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
