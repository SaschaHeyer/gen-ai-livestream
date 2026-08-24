#!/usr/bin/env python3
"""blurlab head-to-head re-scorer.

The speedup metric is wall-clock, so a single measurement is worth little.
Re-running program A five times and then program B five times is worse than
useless, the machine warms up and drifts under the second batch. This script
interleaves instead, one round scores every program in turn, and it reports
the median over rounds.

    python3 compare.py seed.swift best_program.swift claude_best_program.swift
    python3 compare.py --rounds 7 best_program.swift claude_best_program.swift

Output is a markdown table plus results.json in the current directory, with
every individual measurement kept so the spread is visible rather than
averaged away.
"""

import argparse
import json
import statistics
from pathlib import Path

from evaluate import FAILED_SCORE, ensure_goldens, evaluate

LAB = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("programs", nargs="+", help="Swift files to score")
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--out", default="compare-results.json")
    args = parser.parse_args()

    paths = [Path(p) for p in args.programs]
    for path in paths:
        if not path.exists():
            raise SystemExit(f"no such program, {path}")

    manifest = ensure_goldens()
    baseline_ms = manifest["msPerFrame"]

    measurements = {path.name: [] for path in paths}
    for round_index in range(1, args.rounds + 1):
        print(f"round {round_index}/{args.rounds}", flush=True)
        for path in paths:
            scores = evaluate(path.read_text())
            measurements[path.name].append(scores)
            speedup = scores["speedup"]
            shown = "rejected" if speedup == FAILED_SCORE else f"{speedup:.3f}x"
            print(f"  {path.name}, {shown}, ssim {scores.get('ssim', 0):.5f}",
                  flush=True)

    rows = []
    for name, runs in measurements.items():
        speedups = [r["speedup"] for r in runs if r["speedup"] != FAILED_SCORE]
        ssims = sorted({round(r.get("ssim", 0), 5) for r in runs})
        rows.append({
            "program": name,
            "rejected_rounds": len(runs) - len(speedups),
            "speedup_median": round(statistics.median(speedups), 3) if speedups else None,
            "speedup_min": round(min(speedups), 3) if speedups else None,
            "speedup_max": round(max(speedups), 3) if speedups else None,
            "ms_per_frame_median": round(baseline_ms / statistics.median(speedups), 3)
                                  if speedups else None,
            "ssim": ssims[0] if len(ssims) == 1 else ssims,
            "speedups": [round(s, 3) for s in speedups],
        })

    print()
    print(f"baseline (seed) {baseline_ms} ms per frame, "
          f"{manifest['width']}x{manifest['height']}, {manifest['frames']} frames, "
          f"{args.rounds} interleaved rounds")
    print()
    print("| program | median speedup | range | ms per frame | ssim |")
    print("|---|---|---|---|---|")
    for row in rows:
        if row["speedup_median"] is None:
            print(f"| {row['program']} | rejected | | | |")
            continue
        print(f"| {row['program']} | {row['speedup_median']}x | "
              f"{row['speedup_min']}x to {row['speedup_max']}x | "
              f"{row['ms_per_frame_median']} | {row['ssim']} |")

    Path(args.out).write_text(json.dumps(
        {"baseline_ms_per_frame": baseline_ms, "clip": manifest,
         "rounds": args.rounds, "results": rows}, indent=2))
    print(f"\nwritten to {args.out}")


if __name__ == "__main__":
    main()
