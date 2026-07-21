---
name: gemini-token-cost
description: Use this skill when measuring, comparing, or projecting the real cost of a Gemini API prompt, choosing between Gemini models on price, or working out why a Gemini bill is higher than the visible output suggests. Covers the Interactions API usage object, the separate total_thought_tokens field, why billed output equals visible output plus thinking, per model pricing, and the deprecated temperature, top_p and top_k sampling parameters. SDK used, google-genai.
---

# Gemini Token Cost Skill

## Overview

The token count you would naturally reach for is not the one you are billed for. The Gemini
Interactions API reports thinking tokens separately from output tokens, and Google bills thinking
at the full output rate. On short answer workloads the thinking is routinely twenty to thirty times
larger than the visible answer.

- Read the right fields off `usage` so a cost estimate is not silently wrong
- Compare models on real measured cost rather than on headline pricing
- Project a monthly bill from a measured per call cost

> [!IMPORTANT]
> Billed output equals `usage.total_output_tokens` plus `usage.total_thought_tokens`. The pricing
> page states the output price is "including thinking tokens". `usage.total_tokens` is input plus
> output plus thought, so it is not a drop in replacement either. Measured 2026-07-21, a single
> short answer call returned `total_input_tokens` 12, `total_output_tokens` 281,
> `total_thought_tokens` 596, `total_tokens` 889.

> [!IMPORTANT]
> Use `google-genai>=2.3.0`, verified on 2.12.1. The client surface is
> `client.interactions.create(...)` and the clean text accessor is `interaction.output_text`.

> [!WARNING]
> The legacy `google-generativeai` (Python) and `@google/generative-ai` (JavaScript) packages are
> deprecated. Do not use them. `gemini-2.5-*` and `gemini-1.5-*` model IDs are legacy, substitute
> `gemini-3.6-flash`.

> [!WARNING]
> `temperature`, `top_p` and `top_k` were deprecated in the 2026-07-21 changelog. They are not
> merely discouraged, they no longer do anything. See the sampling section below for the exact
> observable symptoms, this one is silent and will not raise.

---

## Quick Start

Read the billed token counts off a single call.

```python
import os
from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

interaction = client.interactions.create(
    model="gemini-3.6-flash",
    input="Name three things worth checking before a livestream goes live.",
)

u = interaction.usage
visible = u.total_output_tokens or 0
thought = u.total_thought_tokens or 0
billed_output = visible + thought

print(interaction.output_text)
print(f"input {u.total_input_tokens}, visible {visible}, thought {thought}")
print(f"billed output {billed_output}")
```

> [!WARNING]
> Do not bill against `total_output_tokens` alone. On a long context short answer call measured
> 2026-07-21, visible output averaged 26 tokens and thinking averaged 833, so costing off the
> visible field alone understated the output bill by more than thirty times.

Turn tokens into money.

```python
PRICES = {                                     # USD per 1M tokens, verified 2026-07-21
    "gemini-3.6-flash":      {"input": 1.50, "output": 7.50},
    "gemini-3.5-flash":      {"input": 1.50, "output": 9.00},
    "gemini-3.5-flash-lite": {"input": 0.30, "output": 2.50},
}

price = PRICES["gemini-3.6-flash"]
cost = (u.total_input_tokens / 1e6) * price["input"] + (billed_output / 1e6) * price["output"]
print(f"{cost:.6f} USD")
```

> [!IMPORTANT]
> Only the output price moved in the 3.6 Flash release. Input stayed at 1.50 per million. That
> matters less than it sounds, see the measured results below, on long context short answer work
> the input was only about sixteen percent of the bill.

---

## Sampling parameters are now a silent no-op

```python
# raises TypeError from the SDK, loud and easy to catch
client.interactions.create(model="gemini-3.6-flash", input=p, temperature=0.2)
# TypeError: create() got unexpected keyword argument(s): temperature.
#            Use extra_body=... to send additional request body fields.

# accepted, validated, and then ignored
client.interactions.create(
    model="gemini-3.6-flash", input=p, generation_config={"temperature": 0.0}
)
```

> [!WARNING]
> Passing `temperature` inside `generation_config` raises nothing and warns nothing, and the value
> is even range validated, `temperature: 999` returns HTTP 400 `invalid_request`. It still has no
> effect on sampling. Observable symptom, `temperature: 0.0` on a high entropy prompt returned 6
> distinct answers out of 6 runs, the same spread as `temperature: 2.0` and as sending no config at
> all (measured 2026-07-21, `gemini-3.6-flash`). If code depends on `temperature: 0` for
> reproducible output, that guarantee is gone and nothing in the response will tell you.

---

## Measured behaviour

All figures measured 2026-07-21 on `google-genai==2.12.1`, Python 3.13.3, 3 samples per model,
comparing `gemini-3.5-flash` against `gemini-3.6-flash`.

| workload shape | visible output change | thinking change | cost change |
| --- | --- | --- | --- |
| long answer, 57 token input | 16.3 percent fewer | 5.7 percent fewer | 28.0 percent cheaper |
| long context, short answer, 1433 token input | 26.7 percent fewer | 32.3 percent fewer | 36.6 percent cheaper |

- Google's headline claim of 17 percent fewer output tokens reproduced closely on the long answer
  shape, 16.3 percent measured.
- Long context short answer work saved MORE, not less, despite the input price being unchanged.
  Thinking dominates that bill, so a model that thinks less wins there.
- 3.6 Flash does not always think less. On an unrelated explanation prompt it produced 791 visible
  tokens against 3.5 Flash's 1050 while thinking MORE, 1115 against 926, and still came out 19.6
  percent cheaper overall. Measure the workload, do not assume the direction.

> [!WARNING]
> Single samples are misleading here, thinking token counts swing hard run to run. Two individual
> runs of the long answer comparison showed 43.6 and 48.4 percent cost savings, while the 3 sample
> average of the same comparison was 28.0 percent. Default to at least 3 samples before drawing a
> conclusion.

---

## Workflow

1. Work out the shape of the user's real workload, long answer or long context short answer, and
   get an actual prompt from them rather than inventing a representative one.
2. Run `scripts/tokencost.py` against that prompt with `--repeat 3` or higher, adding
   `--monthly-calls` when the user has a volume in mind.
3. Report the measured per call cost, the cheapest model, and what share of the bill is thinking.
   State the sample count, and never present a single run as a result.

---

## Supporting files

```
gemini-token-cost/skill/
├── SKILL.md
├── requirements.txt
└── scripts/
    └── tokencost.py
```

- [scripts/tokencost.py](scripts/tokencost.py), measures and compares the real cost of a prompt
  across Gemini models, counting thinking as billed output.

```bash
export GEMINI_API_KEY=...
python scripts/tokencost.py "Explain why database indexes slow down writes."
python scripts/tokencost.py --file prompt.txt --repeat 5
python scripts/tokencost.py --file prompt.txt --models gemini-3.6-flash gemini-3.5-flash-lite
python scripts/tokencost.py --file prompt.txt --repeat 3 --monthly-calls 200000
```

> [!IMPORTANT]
> The price table lives in `PRICES` at the top of the script, as data. When Google moves prices,
> edit that table, it is the only place a rate appears.

---

## Dependencies and Prerequisites

- `google-genai >= 2.3.0`, verified on 2.12.1. Install with `pip install -U google-genai`.
- Python >= 3.10, verified on 3.13.3. The `client.interactions` surface is absent on `google-genai`
  1.x, and pip will silently resolve to 1.x on an older interpreter, which looks exactly like the
  feature never shipped.
- `GEMINI_API_KEY` in the environment.

---

## Documentation Pages

You MUST fetch the matching page below before writing code. These hosted docs are the source of
truth for parameters, types, and edge cases, do not rely solely on the examples above.

- https://ai.google.dev/gemini-api/docs/pricing
- https://ai.google.dev/gemini-api/docs/changelog
- https://ai.google.dev/gemini-api/docs/computer-use
- https://github.com/google-gemini/gemini-skills/blob/main/skills/gemini-interactions-api/SKILL.md

> [!WARNING]
> Built in computer use is not new in the 3.6 Flash release, despite being listed in the
> announcement. It shipped 2026-06-24 with Gemini 3.5 Flash, and the tool worked in
> `gemini-3-pro-preview` and `gemini-3-flash-preview` from 2026-01-29. The computer use tool itself
> is still marked Preview even though the models carrying it are GA.

## From the episode

Built live on the Friday stream, 2026-09-25. Video link to follow.
