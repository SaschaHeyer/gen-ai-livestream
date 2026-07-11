#!/usr/bin/env python3
"""encoderlab evaluator. Scores a candidate encoder configuration by encoding
a fixed program-feed clip and measuring VMAF against the source.

The objective is perceptual quality at the same bandwidth. Candidates are
Python programs whose encoder_args() returns ffmpeg output arguments. Gates,
all hard failures rather than tradeoffs.

  - the encoder must be h264_videotoolbox and the output must decode as h264
  - measured output bitrate within +5 percent of the 12000 kbps target
  - keyframes at most 2.1 seconds apart (YouTube and LinkedIn ingest rules)
  - encode at least realtime (it feeds a live stream)

VMAF is computed with both streams scaled to 1080p (the default model's
training resolution) and is deterministic. Standalone use,

    python3 evaluate.py            # scores seed.py
    python3 evaluate.py cand.py    # scores a candidate

Env overrides, ENCODERLAB_SOURCE (default source.mov next to this file),
ENCODERLAB_TARGET_KBPS (default 12000).
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

LAB = Path(__file__).resolve().parent
SOURCE = Path(os.environ.get("ENCODERLAB_SOURCE", LAB / "source.mov"))
TARGET_KBPS = int(os.environ.get("ENCODERLAB_TARGET_KBPS", "12000"))
BITRATE_TOLERANCE = 1.05
MAX_KEYFRAME_GAP = 2.1
MIN_SPEED = 1.0
VMAF_THREADS = os.cpu_count() or 8

FAILED_SCORE = -1e12
ENCODE_TIMEOUT = 300
VMAF_TIMEOUT = 900


def fail(reason, **extra):
    result = {"vmaf": FAILED_SCORE, "reason": reason}
    result.update(extra)
    return result


def extract_args(code):
    """Exec the candidate and pull encoder_args(). Returns (args, error)."""
    namespace = {}
    try:
        exec(code, namespace)
    except Exception as error:
        return None, f"candidate failed to execute, {error}"
    fn = namespace.get("encoder_args")
    if not callable(fn):
        return None, "candidate has no callable encoder_args()"
    try:
        args = list(fn())
    except Exception as error:
        return None, f"encoder_args() raised, {error}"
    if not all(isinstance(a, str) for a in args):
        return None, "encoder_args() must return a flat list of strings"
    if "h264_videotoolbox" not in args:
        return None, ("the encoder must stay h264_videotoolbox, the app "
                      "encodes on the media engine by design")
    return args, None


def source_duration():
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(SOURCE)],
        capture_output=True, text=True, timeout=60)
    return float(out.stdout.strip())


def probe_output(path):
    """Return (codec, bitrate_kbps, max_keyframe_gap_seconds)."""
    codec = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=60).stdout.strip()
    bitrate = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=bit_rate",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=60).stdout.strip()
    kbps = int(bitrate) / 1000 if bitrate.isdigit() else 0
    packets = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "packet=pts_time,flags", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=120).stdout
    key_times = []
    for line in packets.splitlines():
        parts = line.split(",")
        if len(parts) >= 2 and "K" in parts[1]:
            try:
                key_times.append(float(parts[0]))
            except ValueError:
                pass
    gap = 0.0
    for a, b in zip(key_times, key_times[1:]):
        gap = max(gap, b - a)
    return codec, kbps, gap


def compute_vmaf(distorted):
    """VMAF of distorted vs SOURCE, both scaled to 1080p."""
    graph = (
        "[0:v]scale=1920:1080:flags=bicubic,setpts=PTS-STARTPTS[d];"
        "[1:v]scale=1920:1080:flags=bicubic,setpts=PTS-STARTPTS[r];"
        f"[d][r]libvmaf=n_threads={VMAF_THREADS}"
    )
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(distorted), "-i", str(SOURCE),
         "-lavfi", graph, "-f", "null", "-"],
        capture_output=True, text=True, timeout=VMAF_TIMEOUT)
    match = re.search(r"VMAF score: ([0-9.]+)", result.stderr)
    return float(match.group(1)) if match else None


def evaluate(code):
    """Score one candidate. The AlphaEvolve controller calls this."""
    args, error = extract_args(code)
    if error:
        return fail(error)

    duration = source_duration()
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out.mp4"
        start = time.monotonic()
        try:
            encode = subprocess.run(
                ["ffmpeg", "-y", "-hide_banner", "-i", str(SOURCE)]
                + args + ["-an", str(out)],
                capture_output=True, text=True, timeout=ENCODE_TIMEOUT)
        except subprocess.TimeoutExpired:
            return fail("encode timed out")
        wall = time.monotonic() - start
        if encode.returncode != 0 or not out.exists():
            return fail(f"ffmpeg rejected the arguments, {encode.stderr[-600:]}")

        speed = duration / wall
        codec, kbps, keyframe_gap = probe_output(out)
        if codec != "h264":
            return fail(f"output codec is {codec}, must be h264",
                        bitrate_kbps=kbps)
        if kbps > TARGET_KBPS * BITRATE_TOLERANCE:
            return fail(f"bitrate {kbps:.0f} kbps exceeds the "
                        f"{TARGET_KBPS} kbps budget", bitrate_kbps=kbps)
        if keyframe_gap > MAX_KEYFRAME_GAP:
            return fail(f"keyframe gap {keyframe_gap:.2f}s exceeds "
                        f"{MAX_KEYFRAME_GAP}s, streaming platforms reject this",
                        bitrate_kbps=kbps)
        if speed < MIN_SPEED:
            return fail(f"encode speed {speed:.2f}x is below realtime",
                        bitrate_kbps=kbps)

        vmaf = compute_vmaf(out)
    if vmaf is None:
        return fail("VMAF computation failed")
    return {"vmaf": vmaf, "bitrate_kbps": round(kbps), "encode_speed": round(speed, 2)}


if __name__ == "__main__":
    if not SOURCE.exists():
        sys.exit(f"no source clip at {SOURCE}")
    candidate = Path(sys.argv[1]) if len(sys.argv) > 1 else LAB / "seed.py"
    print(json.dumps(evaluate(candidate.read_text()), indent=2))
