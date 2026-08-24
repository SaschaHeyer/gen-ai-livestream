#!/usr/bin/env python3
"""blurlab floor probe. How much of a candidate's measured time is the kernel,
and how much is the harness charging it for existing?

The bench times `process()` plus `ciContext.render()` of a full 1080p frame.
The render is unavoidable, every kernel pays it, so there is a hard floor below
which no correct program can score. This measures that floor with a kernel that
does nothing at all (it returns the input frame, fails the SSIM gate by design,
we only want its milliseconds), and puts the real programs next to it.

That comparison decides whether a head-to-head is meaningful. If two winners
are both within noise of the floor, the metric has saturated and their
difference is not a fact about the code.

    python3 harness_floor.py                       # floor vs seed and both winners
    python3 harness_floor.py --rounds 7 a.swift b.swift

Programs are run interleaved, one round scores each in turn, because the score
is wall-clock and the machine drifts as it warms.
"""

import argparse
import json
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

LAB = Path(__file__).resolve().parent
BENCH = LAB / "bench.swift"
CLIP = LAB / "clip.mov"
GOLDENS = LAB / "goldens"

PASSTHROUGH = """// Floor probe. Does no work, just hands the frame back, so the
// bench measures only the cost of the timed region itself.
import CoreImage
import Vision

final class EvolvedBlurKernel {
    func process(_ pixelBuffer: CVPixelBuffer, frameIndex: Int,
                 ciContext: CIContext) -> CIImage {
        return CIImage(cvPixelBuffer: pixelBuffer)
    }
}
"""

DEFAULTS = ["seed.swift", "best_program.swift", "claude_best_program.swift",
            "claude_agentic_best_program.swift"]


def compile_one(source_text, workdir, name):
    src = workdir / f"{name}.swift"
    src.write_text(source_text)
    binary = workdir / name
    result = subprocess.run(
        ["swiftc", "-O", str(BENCH), str(src), "-o", str(binary)],
        capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        sys.exit(f"{name} failed to compile\n{result.stderr[-1500:]}")
    return binary


def run_one(binary, frames):
    result = subprocess.run(
        [str(binary), "--clip", str(CLIP), "--frames", str(frames),
         "--golden", str(GOLDENS)],
        capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        sys.exit(f"bench failed\n{result.stderr[-1000:]}")
    return json.loads(result.stdout.strip().splitlines()[-1])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("programs", nargs="*", default=DEFAULTS)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--out", default="harness-floor.json")
    args = parser.parse_args()

    manifest = json.loads((GOLDENS / "manifest.json").read_text())
    programs = [Path(p) for p in (args.programs or DEFAULTS)]
    for path in programs:
        if not path.exists():
            sys.exit(f"no such program, {path}")

    with tempfile.TemporaryDirectory(prefix="blurlab-floor-") as tmp:
        workdir = Path(tmp)
        print("compiling", flush=True)
        binaries = [("floor (does nothing)",
                     compile_one(PASSTHROUGH, workdir, "floor"))]
        for i, path in enumerate(programs):
            binaries.append((path.name,
                             compile_one(path.read_text(), workdir, f"p{i}")))

        samples = {name: [] for name, _ in binaries}
        for round_index in range(1, args.rounds + 1):
            print(f"round {round_index}/{args.rounds}", flush=True)
            for name, binary in binaries:
                result = run_one(binary, args.frames)
                samples[name].append(result["msPerFrame"])
                print(f"  {name}, {result['msPerFrame']} ms", flush=True)

    floor = statistics.median(samples["floor (does nothing)"])
    print(f"\nbaseline (seed at golden-render time) "
          f"{manifest['msPerFrame']} ms per frame, "
          f"{manifest['width']}x{manifest['height']}, {args.rounds} rounds\n")
    print("| program | median ms | range | above the floor | speedup ceiling |")
    print("|---|---|---|---|---|")
    rows = []
    for name, _ in binaries:
        values = samples[name]
        median = statistics.median(values)
        above = median - floor
        rows.append({"program": name, "median_ms": round(median, 3),
                     "min_ms": min(values), "max_ms": max(values),
                     "ms_above_floor": round(above, 3),
                     "samples": values})
        ceiling = manifest["msPerFrame"] / median if median > 0 else 0
        print(f"| {name} | {median:.3f} | {min(values):.3f} to {max(values):.3f} "
              f"| {above:+.3f} | {ceiling:.2f}x |")

    print(f"\nThe floor is {floor:.3f} ms. Any program whose time above the "
          f"floor is comparable to\nthe floor's own spread "
          f"({max(samples['floor (does nothing)']) - min(samples['floor (does nothing)']):.3f} ms) "
          f"is not being measured, it is being\nrounded. The best possible "
          f"score on this harness is "
          f"{manifest['msPerFrame'] / floor:.2f}x.")

    Path(args.out).write_text(json.dumps(
        {"baseline_ms_per_frame": manifest["msPerFrame"], "rounds": args.rounds,
         "floor_ms": round(floor, 3), "results": rows}, indent=2))
    print(f"\nwritten to {args.out}")


if __name__ == "__main__":
    main()
