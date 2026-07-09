---
name: agent-eval-flywheel
description: >
  Use this skill to evaluate an ADK agent with Google's Agent Quality Flywheel, run an evalset,
  choose the right metric, and read the results. Covers the ADK metric menu and which metrics run
  locally versus which call an AI judge, how the LLM judge scores meaning rather than words, how a
  rubric judge writes a plain-English reason for each verdict graded against trusted evidence, and
  how to close the eval fix loop. SDKs and tools used, agents-cli, adk eval, google-adk[eval], the
  Gemini API for the agent and the judge.
---

# Agent Eval Flywheel Skill

How Google grades AI agents, and how you drive the loop. You pick a metric that matches what you care
about, run the eval, read what the judge says, and refine. The payoff is a judge that scores an
answer's meaning and explains its verdict in plain English, a score you can act on.

> [!IMPORTANT]
> Two skills ship this workflow. `google-agents-cli-eval` drives ADK agents through `agents-cli eval
> run` (which wraps `adk eval`). `agent-platform-eval-flywheel` is the framework agnostic sibling for
> the cloud Evaluation SDK. This skill covers the local ADK path, which needs nothing but the Gemini
> API key.

> [!IMPORTANT]
> The metric menu is the whole mental model. Two metrics run LOCALLY and free, `tool_trajectory_avg_score`
> (did it call the right tools) and `response_match_score` (does the text match a reference). The rest
> are LLM as judge, `final_response_match_v2`, `rubric_based_final_response_quality_v1`,
> `rubric_based_tool_use_quality_v1`, `hallucinations_v1`, and `safety_v1`. First decision every time,
> do you care about the exact words or the meaning. Words, use a local metric. Meaning, use a judge.

---

## Quick Start

The full eval fix loop, all verified against google-adk 2.4.0 on Python 3.12 with the Gemini API key.

```bash
# 1. Environment. The agent AND the judge both call the Gemini API.
export GOOGLE_GENAI_USE_VERTEXAI=0
export GOOGLE_API_KEY=YOUR_AI_STUDIO_KEY

# 2. Grade with the free local metrics.
adk eval ./episode_finder tests/eval/evalsets/episode_finder.evalset.json \
  --config_file_path tests/eval/eval_config.json --print_detailed_results
#   tool_trajectory_avg_score  PASSED 1.0   <- it called the right tool

# 3. Add an AI judge. It scores MEANING, not words.
adk eval ./episode_finder tests/eval/evalsets/episode_finder.evalset.json \
  --config_file_path tests/eval/eval_config_judge.json --print_detailed_results
#   final_response_match_v2    PASSED 1.0

# 4. Close the loop. Keep tool trajectory plus the judge, rerun, all green.
adk eval ./episode_finder tests/eval/evalsets/episode_finder.evalset.json \
  --config_file_path tests/eval/eval_config_fixed.json --print_detailed_results
```

> [!NOTE]
> `response_match_score` is ROUGE, it compares words. A correct answer worded differently from your
> reference scores low (measured 0.2 to 0.35 on this agent, always under the 0.5 threshold). That is
> not a broken agent, it is the signal to use a judge when you care about meaning, not exact wording.

> [!WARNING]
> `adk eval` needs the eval extra. A bare `pip install google-adk` gives `Error: Eval module is not
> installed, please install via pip install "google-adk[eval]"`. Install `google-adk[eval]`.

> [!WARNING]
> The system macOS Python is 3.9, google-adk needs 3.10 or newer. Stand up a current interpreter,
> `uv venv --python 3.12`, before installing.

### The judge that explains itself

The best part of the toolkit. A rubric judge grades against plain-English rules you write, and writes
a reason for each one, against the trusted answer. `adk eval` prints scores but drops the rationale
into a history JSON under `AGENT_DIR/.adk/eval_history/`, so `eval_report.py` surfaces it.

```bash
python eval_report.py ./episode_finder \
  tests/eval/evalsets/episode_finder.evalset.json \
  --config tests/eval/eval_config_rubric.json
```

Real output, the judge grading against the trusted evidence.

```
Q  Which Stage Studio episode covered background agents?
A  Episode e02, titled "Managed Agents background and remote MCP", covered background agents.
   rubric_based_final_response_quality_v1: PASSED score=1.0
      why [names_episode_id] 1.0: states "Episode e02", consistent with the trusted evidence.
      why [names_title] 1.0: includes the title "Managed Agents background and remote MCP".
      why [no_guessing] 1.0: only the episode id and title from the find_episode tool, nothing invented.
```

> [!IMPORTANT]
> The judge is decoupled by design. Whatever wrote the answer, your agent, an optimizer, or you, does
> NOT grade it. A separate judge model call scores it against the reference and writes the reason.
> Keeping the optimizer and the grader apart is the point of the flywheel.

## Workflow

When asked to evaluate an ADK agent, follow this loop.

1. Analyze the goal. Care about MEANING, reach for an LLM judge. Care about the exact tool sequence,
   use `tool_trajectory_avg_score`, local and free.
2. Run `eval_report.py AGENT_DIR EVALSET --config CONFIG` so you see the judge's reasons, not just
   red or green numbers.
3. Read the reason, make one change, rerun. Expect several iterations on a real agent, that is normal,
   each pass makes it better.

## Dependencies and Prerequisites

- Python 3.10 or newer (`uv venv --python 3.12` if the system Python is 3.9).
- `google-adk[eval] >= 2.4.0`, install `uv pip install "google-adk[eval]"`.
- `agents-cli` optional, for the wrapped `agents-cli eval run` command,
  `uv tool install google-agents-cli`. Verified at 0.1.1, 1.0.0 is available.
- A Gemini API key for both the agent and the judge, or Vertex via
  `GOOGLE_GENAI_USE_VERTEXAI=1` and a project.

> [!NOTE]
> Automatic Loss Analysis (failure clustering) and adaptive AutoRaters that write a feedback paragraph
> are Gemini Enterprise Agent Platform features, the cloud product, not the local `adk eval` path.
> Locally the per rubric rationale above is the closest thing to that, and it is most of the value.

## Supporting files

- [scripts/eval_report.py](scripts/eval_report.py), run any agent and evalset and print the judge's
  per rubric reasons. `python eval_report.py AGENT_DIR EVALSET --config CONFIG`.
- [scripts/episode_finder/](scripts/episode_finder/), the tiny verified demo agent, a helper with one
  find_episode tool.
- [scripts/tests/eval/evalsets/episode_finder.evalset.json](scripts/tests/eval/evalsets/episode_finder.evalset.json), a two case evalset.
- [scripts/tests/eval/eval_config.json](scripts/tests/eval/eval_config.json), local metrics only.
- [scripts/tests/eval/eval_config_judge.json](scripts/tests/eval/eval_config_judge.json), adds the AI judge `final_response_match_v2`.
- [scripts/tests/eval/eval_config_fixed.json](scripts/tests/eval/eval_config_fixed.json), tool trajectory plus the judge, all green.
- [scripts/tests/eval/eval_config_rubric.json](scripts/tests/eval/eval_config_rubric.json), rubric judge with three rules, the reasons come from here.

## Documentation Pages

You MUST fetch the matching page below before writing eval code. These hosted docs are the source of
truth for the metric names, config schema, and thresholds, do not rely solely on the examples above.

- https://github.com/google/agents-cli
- https://github.com/google/skills
- https://developers.googleblog.com/driving-the-agent-quality-flywheel-from-your-coding-agent/

## From the episode

Video, link once it is up.
