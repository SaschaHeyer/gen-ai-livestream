#!/usr/bin/env python3
"""Fail the build if the committed golden file no longer matches source.

Regenerate from fragments, diff against the committed artifact. Green means
your repo is exactly what your agent runs. Red means source drifted.
"""
import argparse
import difflib
import sys
from pathlib import Path

from transpile import transpile


def main():
    ap = argparse.ArgumentParser(description="Drift check a committed golden prompt against source.")
    ap.add_argument("entry")
    ap.add_argument("golden", help="the committed golden file to check")
    ap.add_argument("--root", default=".")
    ap.add_argument("--set", action="append", default=[], metavar="k=v")
    args = ap.parse_args()

    context = {}
    for pair in args.set:
        k, _, v = pair.partition("=")
        if v in ("true", "false"):
            v = (v == "true")
        context[k] = v

    fresh = transpile(Path(args.root), args.entry, context)
    committed = Path(args.golden).read_text()

    if fresh == committed:
        print(f"OK: {args.golden} matches source, no drift")
        return 0

    print(f"DRIFT DETECTED: {args.golden} does not match a fresh build\n")
    diff = difflib.unified_diff(
        committed.splitlines(keepends=True),
        fresh.splitlines(keepends=True),
        fromfile=f"{args.golden} (committed)",
        tofile="fresh build from source",
    )
    sys.stdout.writelines(diff)
    return 1


if __name__ == "__main__":
    sys.exit(main())
