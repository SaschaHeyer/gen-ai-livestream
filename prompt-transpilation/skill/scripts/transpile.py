#!/usr/bin/env python3
"""Transpile modular prompt fragments into a single rendered golden file.

Build a prompt the way you build code: resolve includes, inject variables,
validate the wiring, and fail the build before anything reaches the model.
"""
import argparse
import re
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from jinja2.exceptions import TemplateNotFound, UndefinedError

INCLUDE_RE = re.compile(r'{%-?\s*include\s+["\']([^"\']+)["\']')


def build_include_graph(root: Path):
    """Map every fragment to the fragments it includes (static parse, pre-render)."""
    graph = {}
    for path in root.rglob("*.prompt.md"):
        rel = str(path.relative_to(root))
        text = path.read_text()
        graph[rel] = INCLUDE_RE.findall(text)
    return graph


def find_cycle(graph, start):
    """Return the first include cycle reachable from start, or None."""
    stack = []
    seen = set()

    def walk(node):
        if node in stack:
            return stack[stack.index(node):] + [node]
        if node in seen or node not in graph:
            return None
        seen.add(node)
        stack.append(node)
        for dep in graph.get(node, []):
            cycle = walk(dep)
            if cycle:
                return cycle
        stack.pop()
        return None

    return walk(start)


def transpile(root: Path, entry: str, context: dict) -> str:
    graph = build_include_graph(root)

    # Build-time check 1: circular imports, caught before render.
    cycle = find_cycle(graph, entry)
    if cycle:
        raise SystemExit("BUILD FAILED: circular import -> " + " -> ".join(cycle))

    env = Environment(
        loader=FileSystemLoader(str(root)),
        undefined=StrictUndefined,       # Build-time check 2: missing variables raise, not silently blank
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    try:
        tmpl = env.get_template(entry)
        return tmpl.render(**context)
    except TemplateNotFound as e:
        raise SystemExit(f"BUILD FAILED: missing include -> {e}")
    except UndefinedError as e:
        raise SystemExit(f"BUILD FAILED: undefined variable -> {e}")


def main():
    ap = argparse.ArgumentParser(description="Transpile prompt fragments into a golden file.")
    ap.add_argument("entry", help="entry template, relative to --root, e.g. agents/stream_ops_agent.prompt.md")
    ap.add_argument("--root", default=".", help="fragment source root")
    ap.add_argument("--set", action="append", default=[], metavar="k=v", help="template variable, repeatable")
    ap.add_argument("--out", help="write golden file here instead of stdout")
    args = ap.parse_args()

    context = {}
    for pair in args.set:
        k, _, v = pair.partition("=")
        if v in ("true", "false"):
            v = (v == "true")
        context[k] = v

    rendered = transpile(Path(args.root), args.entry, context)
    if args.out:
        Path(args.out).write_text(rendered)
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(rendered)


if __name__ == "__main__":
    main()
