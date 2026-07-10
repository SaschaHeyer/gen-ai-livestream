#!/usr/bin/env python3
"""blurlab evaluator. Compiles a candidate blur kernel against the bench
harness, runs it over the fixed clip, and scores it against the goldens.

This is the objective function for AlphaEvolve. It returns a dict of
metric name to scalar, higher is better. The primary metric is speedup,
baseline milliseconds per frame divided by candidate milliseconds per
frame, gated by an SSIM floor so a candidate can never win by looking
different.

Standalone use, score the seed (expect speedup near 1.0, ssim 1.0).

    python3 evaluate.py            # scores seed.swift
    python3 evaluate.py cand.swift # scores a specific candidate

Configuration through env vars.

    BLURLAB_CLIP    path to the clip, default clip.mov next to this file
    BLURLAB_FRAMES  frames to evaluate, default 60
    BLURLAB_SYNTHETIC=1  use synthetic frames (smoke test only)
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

LAB = Path(__file__).resolve().parent
BENCH_SOURCE = LAB / "bench.swift"
SEED = LAB / "seed.swift"
GOLDEN_DIR = LAB / "goldens"
CLIP = Path(os.environ.get("BLURLAB_CLIP", LAB / "clip.mov"))
FRAMES = int(os.environ.get("BLURLAB_FRAMES", "60"))
SYNTHETIC = os.environ.get("BLURLAB_SYNTHETIC") == "1"

# A candidate below these floors is visually different, not faster.
SSIM_MEAN_FLOOR = 0.98
SSIM_MIN_FLOOR = 0.95

# Sentinel for invalid candidates, matches the AlphaEvolve convention.
FAILED_SCORE = -1e12
FAILED = {"speedup": FAILED_SCORE, "ssim": 0.0}

COMPILE_TIMEOUT = 180
RUN_TIMEOUT = 600


def input_args():
    args = ["--frames", str(FRAMES)]
    if SYNTHETIC:
        args.append("--synthetic")
    else:
        args += ["--clip", str(CLIP)]
    return args


def compile_candidate(code, workdir):
    """Returns the compiled binary path, or None on failure."""
    candidate = workdir / "candidate.swift"
    candidate.write_text(code)
    binary = workdir / "bench-bin"
    try:
        result = subprocess.run(
            ["swiftc", "-O", str(BENCH_SOURCE), str(candidate), "-o", str(binary)],
            capture_output=True, text=True, timeout=COMPILE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return None
    if result.returncode != 0:
        print(f"compile failed\n{result.stderr[-2000:]}", file=sys.stderr)
        return None
    return binary


def run_bench(binary, extra_args):
    """Returns the parsed JSON metrics dict, or None on failure."""
    try:
        result = subprocess.run(
            [str(binary)] + input_args() + extra_args,
            capture_output=True, text=True, timeout=RUN_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return None
    if result.returncode != 0:
        print(f"bench failed\n{result.stderr[-2000:]}", file=sys.stderr)
        return None
    try:
        return json.loads(result.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        print(f"bench produced no JSON\n{result.stdout[-500:]}", file=sys.stderr)
        return None


def ensure_goldens():
    """Render the goldens from the seed once, return the manifest."""
    manifest_path = GOLDEN_DIR / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("frames") == FRAMES:
            return manifest
        print("golden frame count changed, re-rendering goldens", file=sys.stderr)
    if not SYNTHETIC and not CLIP.exists():
        sys.exit(f"no clip at {CLIP}. Record a short webcam take (QuickTime, "
                 "File > New Movie Recording) and save it there, or set BLURLAB_CLIP.")
    with tempfile.TemporaryDirectory() as tmp:
        binary = compile_candidate(SEED.read_text(), Path(tmp))
        if binary is None:
            sys.exit("the seed itself failed to compile, fix seed.swift first")
        result = run_bench(binary, ["--write-golden", str(GOLDEN_DIR)])
        if result is None:
            sys.exit("golden render failed")
    return json.loads(manifest_path.read_text())


def evaluate(code):
    """Score one candidate. The AlphaEvolve controller calls this."""
    manifest = ensure_goldens()
    baseline_ms = manifest["msPerFrame"]
    with tempfile.TemporaryDirectory() as tmp:
        binary = compile_candidate(code, Path(tmp))
        if binary is None:
            return dict(FAILED)
        result = run_bench(binary, ["--golden", str(GOLDEN_DIR)])
    if result is None:
        return dict(FAILED)
    ssim = result.get("ssim", 0.0)
    ssim_min = result.get("ssimMin", 0.0)
    ms = result.get("msPerFrame", 0.0)
    if ms <= 0:
        return dict(FAILED)
    if ssim < SSIM_MEAN_FLOOR or ssim_min < SSIM_MIN_FLOOR:
        # Visually broken. Report the real ssim so the evolver learns why.
        return {"speedup": FAILED_SCORE, "ssim": ssim}
    return {"speedup": baseline_ms / ms, "ssim": ssim}


if __name__ == "__main__":
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else SEED
    scores = evaluate(source.read_text())
    print(json.dumps(scores, indent=2))
