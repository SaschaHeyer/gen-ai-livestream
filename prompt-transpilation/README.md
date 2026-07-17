# Prompt Transpilation

Treat your agent's system prompt like a build artifact, not one giant hand-edited file. Author modular fragments, transpile them into a single rendered golden file, validate the wiring at build time, and drift-check it in CI.

Based on Google's Developers Blog post [Building scalable AI agents with modular prompt transpilation](https://developers.googleblog.com/building-scalable-ai-agents-with-modular-prompt-transpilation/), which describes the pattern but ships no code. This is the working implementation.

## What is here

- [skill/SKILL.md](skill/SKILL.md) the installable skill, quick start, gotchas, and workflow.
- [skill/scripts/transpile.py](skill/scripts/transpile.py) render modular fragments into a golden file, with build-time checks for missing variables and circular imports.
- [skill/scripts/drift_check.py](skill/scripts/drift_check.py) fail the build when a committed golden file no longer matches source.
- [skill/examples/](skill/examples/) a runnable reproduction, one entry template plus two shared fragments.

## Quick Start

```bash
pip install "jinja2>=3.1.0"
cd skill/examples
python ../scripts/transpile.py agents/stream_ops_agent.prompt.md --root . \
  --set environment=production --set allow_remediation=true --set city=Berlin \
  --out build/stream_ops_agent.golden.md
```

Install the skill for your agent:

```bash
npx skills add prompt-transpilation
```
