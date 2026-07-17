---
name: prompt-transpilation
description: Use this skill when you want to treat agent system prompts like build artifacts instead of one giant hand-edited file. Covers authoring modular prompt fragments, transpiling them into a single rendered golden file with Jinja2, build-time validation for missing variables and circular imports, and CI drift checks that keep the committed prompt equal to source. Tools used, Python, Jinja2. Ships two runnable utilities, transpile.py and drift_check.py.
---

# Prompt Transpilation Skill

Build a prompt the way you build code. Author modular fragments, compose them with includes and variables, render one deterministic golden file, and fail the build before a broken prompt ever reaches the model.

## Overview

- Split a monolithic system prompt into modular `*.prompt.md` fragments and compose them with Jinja2 `{% include %}`, `{% if %}`, and `{% macro %}`.
- Transpile the entry template plus variables into one fully rendered golden file, the exact text the model sees.
- Catch two whole classes of bug at build time, undefined variables and circular includes.
- Drift-check the committed golden file against a fresh build in CI so your repo is always exactly what runs.

> [!IMPORTANT]
> This pattern comes from Google's Developers Blog post, "Building scalable AI agents with modular prompt transpilation" (July 16 2026). That post describes the idea but ships no code. This skill is the working implementation, verified end to end. The transpiler is Jinja2 plus a diff, there is no new Google product or SDK behind it.

> [!WARNING]
> The "dynamic skills / progressive disclosure" half of the source post, an agent loading only the skill modules a task needs at runtime, is the Agent Skills model that already shipped, see agentskills.io and github.com/google-gemini/gemini-skills. Do not reimplement it here, reuse it. This skill is only the build-and-validate layer for the prompts themselves.

---

## Quick Start

Install:

```bash
pip install "jinja2>=3.1.0"
```

Author fragments, an entry template that includes shared pieces and takes variables:

```jinja
{% macro bullet_section(title, items) -%}
## {{ title.rstrip() }}
{% for item in items -%}
- {{ item.rstrip() }}
{% endfor %}
{%- endmacro -%}
{% include "shared/safety.prompt.md" %}
{% include "shared/tool_usage.prompt.md" %}

You are a livestream operations agent for a show broadcasting from {{ city }} in the {{ environment }} environment.

{% if allow_remediation %}
You may recommend and, with approval, apply remediation steps when a stream goes down.
{% else %}
You may inspect, summarize, and explain a stream incident, but do not apply remediation actions.
{% endif %}
```

> [!NOTE]
> `title.rstrip()` and other string methods work fine in Jinja2, including in a `SandboxedEnvironment`. Verified on jinja2 3.1.6. If you read anywhere that Jinja blocks string methods by default, that is wrong, only genuinely unsafe attribute access is blocked.

Transpile it into a golden file:

```bash
python scripts/transpile.py agents/stream_ops_agent.prompt.md --root . \
  --set environment=production --set allow_remediation=true --set city=Berlin \
  --out build/stream_ops_agent.golden.md
```

One template gives you every environment. Same command with `--set environment=dev --set allow_remediation=false` renders the inspect-only variant, the `{% else %}` branch, from the same source.

Drift-check the committed golden file in CI:

```bash
python scripts/drift_check.py agents/stream_ops_agent.prompt.md build/stream_ops_agent.golden.md \
  --root . --set environment=production --set allow_remediation=true --set city=Berlin
```

Exit 0 and "no drift" when the committed file matches a fresh build, exit 1 with a unified diff when it does not. Wire it as a CI step so a fragment edit that was never rebuilt fails the pipeline.

## Gotchas earned building this

> [!WARNING]
> By default Jinja2 renders an undefined variable as an empty string, silently. Forget to pass `city` and you get "broadcasting from  in production", the word just vanishes and nothing errors. This is the exact deferred-runtime-error class the whole pattern is meant to kill. The fix is one line, construct the environment with `undefined=StrictUndefined`, and a missing variable raises `UndefinedError` at build time. `transpile.py` already does this.

> [!WARNING]
> Raw Jinja2 does not give you a useful error on a circular include, `safety` includes `tool_usage`, `tool_usage` includes `safety`. It blows the stack with `RecursionError: maximum recursion depth exceeded`, which tells you nothing about which files loop. `transpile.py` parses the include graph statically BEFORE rendering and fails with the actual cycle, `shared/safety.prompt.md -> shared/tool_usage.prompt.md -> shared/safety.prompt.md`.

> [!WARNING]
> Includes resolve relative to the Jinja loader root, not the entry file. Point `--root` at the wrong folder and every include dies with `TemplateNotFound`. Set the root explicitly and run one render to confirm before you trust it.

> [!NOTE]
> Whitespace matters. `transpile.py` sets `trim_blocks=True` and `lstrip_blocks=True`, and the macro uses `{%- -%}` markers, so control lines do not leave blank-line noise in the rendered prompt. Drop these and your golden file fills with empty lines that change on every edit and make drift diffs unreadable.

## Workflow

1. Read the request, identify the entry template and the variables it needs (environment, feature flags, per-deployment values).
2. Run `scripts/transpile.py <entry> --root <fragments_dir> --set k=v ... --out <golden>` to build the golden file. If it fails, the message names the missing variable or the include cycle, fix the source, not the golden file.
3. To validate an existing commit, run `scripts/drift_check.py <entry> <golden> --root <dir> --set ...`. Non-zero exit means source drifted, rebuild and commit the golden file.
4. Report the golden file path and the build result back.

## Supporting files

- [scripts/transpile.py](scripts/transpile.py) transpile fragments into a golden file. `python scripts/transpile.py agents/stream_ops_agent.prompt.md --root . --set environment=production --set allow_remediation=true --set city=Berlin --out build/out.md`
- [scripts/drift_check.py](scripts/drift_check.py) fail if a committed golden file drifted from source. `python scripts/drift_check.py agents/stream_ops_agent.prompt.md build/out.md --root . --set environment=production --set allow_remediation=true --set city=Berlin`
- [examples/](examples/) the frozen reproduction from the episode, one entry template plus two shared fragments, point the scripts here to see a clean build and both failure modes.

## Dependencies and Prerequisites

- Python 3.7 or newer.
- `jinja2 >= 3.1.0`, verified on 3.1.6.
- Install, `pip install "jinja2>=3.1.0"`.

## Documentation Pages

Source article, background reading, not required to run the code.

- https://developers.googleblog.com/building-scalable-ai-agents-with-modular-prompt-transpilation/

## From the episode

Full walkthrough, building a prompt build system live, video link to follow.
