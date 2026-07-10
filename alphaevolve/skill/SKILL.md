---
name: alphaevolve
description: Use this skill when running Google's AlphaEvolve, the Gemini-powered evolutionary coding agent, to discover or optimize an algorithm on Google Cloud. Covers wrapping a function in EVOLVE-BLOCK markers, writing a scoring function, driving the controller loop against a Gemini Enterprise engine, reading back the best evolved program, and the license, cost, and non-monotonic-progress gotchas. Uses the alpha_evolve client library, Discovery Engine, gemini-3.5-flash and gemini-3.1-pro-preview.
---

# AlphaEvolve on Google Cloud Skill

Point AlphaEvolve at a function you wrote and let it evolve a better one. You supply a seed program and a scoring function, AlphaEvolve uses a Gemini ensemble to propose variants, scores each with your evaluator, and climbs toward a higher score over many generations.

> [!IMPORTANT]
> AlphaEvolve went generally available on the Gemini Enterprise agent platform on 2026-07-10. Access requires a **Gemini Enterprise license**, any tier including a trial. It is not on a free tier. The `GE_APP_ID` you pass is the Engine ID of your Gemini Enterprise app, an existing app works, you do not need a fresh one.

> [!IMPORTANT]
> Generation models are `gemini-3.5-flash` and `gemini-3.1-pro-preview`, blended by weight. `gemini-3.1-pro-preview` is served from the `global` location only. Verified working mixture is 0.7 flash, 0.3 pro.

> [!WARNING]
> AlphaEvolve is not a new capability and it is not a coding assistant. The system is DeepMind research from 2025, what shipped in 2026 is general availability plus this open source client library. It is an optimizer for problems where you can put a number on the answer, not autocomplete, not linting, not general code generation. If you cannot write a scoring function, this is the wrong tool.

---

## Quick Start

Mark the region to evolve, and define an `evaluate()` that returns `{metric: score}` where higher is better.

```python
# EVOLVE-BLOCK-START
import numpy as np
def construct_packing(n, random_seed):
    ...          # AlphaEvolve rewrites everything inside this block
# EVOLVE-BLOCK-END

def evaluate(eval_inputs):
    centers, radii, total = construct_packing(eval_inputs["n"], 42)
    return {"sum_of_radii": float(total)}   # the score AlphaEvolve maximizes
```

Then point the `evolve.py` utility at it. This is the whole loop, one command.

```bash
gcloud auth application-default login          # once, ADC for the client
export PROJECT_ID=your-project GE_APP_ID=your-gemini-enterprise-engine-id

python scripts/evolve.py \
  --program scripts/examples/circle_packing.py \
  --metric sum_of_radii --inputs '{"n": 26}' \
  --max-programs 20 --out best_program.py
```

> [!WARNING]
> The client authenticates with Application Default Credentials, so `gcloud auth application-default login` must run first. A plain `gcloud auth login` is not enough, the library uses ADC specifically and will raise `RefreshError: Reauthentication is needed` if ADC is stale.

**Measured on a real n=26 circle packing run** (project with Gemini Enterprise, 0.7 flash / 0.3 pro, `--max-programs 20`): the naive seed scores `sum_of_radii = 0.9415`, the best evolved program scores `2.6294`, a **2.79x** improvement and essentially the known optimum for this problem. Wall clock was about 7.5 minutes.

> [!WARNING]
> **Progress is non-monotonic, do not stop early.** On the real run the scores went 0.9415 seed, then a candidate at 2.36, then one back down at 0.24, then 1.97, then eventually 2.63. The best score plateaus and jumps, a flat stretch is not a stuck run.

> [!WARNING]
> **Invalid candidates are expected and are a signal, not an error.** A candidate that breaks a constraint or fails to run comes back with the sentinel score `-1e12` (a big negative number, not `-inf`, the API needs a real number). On the real 20 program run 4 candidates came back at exactly `-1e12`. Their insight messages are fed back to steer the next generation.

> [!WARNING]
> **The backend can finish before it hits your budget.** The controller loop stops itself after 120 seconds with no new candidates and an empty queue. The real `--max-programs 20` run stopped at 19 of 20 evaluated when the service went idle. This is normal, treat the budget as a ceiling, not a guarantee.

> [!IMPORTANT]
> **The scoring function is the whole game.** AlphaEvolve can only optimize what your `evaluate()` measures. A lazy scorer gets lazy evolution. Almost all of your effort belongs in the evaluator, the client wiring is boilerplate.

---

## Workflow

When a user wants to optimize or discover an algorithm with AlphaEvolve:

1. Confirm they have a Gemini Enterprise license and a `GE_APP_ID` (their Gemini Enterprise app engine id), and that they have run `gcloud auth application-default login`.
2. Wrap the region to evolve in `# EVOLVE-BLOCK-START` / `# EVOLVE-BLOCK-END` and write an `evaluate(inputs)` returning `{metric: score}`, higher is better. Everything outside the markers is left untouched.
3. Run `scripts/evolve.py --program <file> --metric <name> --inputs '<json>' --max-programs <N>`. Start small (`--max-programs 10`) to confirm the loop, then raise the budget.
4. Report the best score and the winning program path back, and compare it to the seed baseline so the improvement is concrete.

---

## Dependencies and Prerequisites

The `alpha_evolve` client library is not on PyPI, it installs from Google's repo.

```bash
git clone https://github.com/Google-Cloud-AI/alphaevolve-on-googlecloud.git
cd alphaevolve-on-googlecloud
uv pip install -e ".[examples]"     # installs alpha_evolve + numpy, matplotlib, etc.
```

- Python 3.9 or newer (verified on 3.12), `uv`, and the `gcloud` CLI.
- A Google Cloud project with a Gemini Enterprise license and Discovery Engine enabled (`gcloud services enable discoveryengine.googleapis.com`).
- `scripts/evolve.py` also needs `nest-asyncio` and `python-dotenv`, see `requirements.txt`.

## Supporting files

- [scripts/evolve.py](scripts/evolve.py) — the utility. Point it at any program with EVOLVE-BLOCK markers and an `evaluate()`, it drives the full AlphaEvolve loop and writes the best program. Run `python scripts/evolve.py --program scripts/examples/circle_packing.py --metric sum_of_radii --inputs '{"n": 26}' --max-programs 20`.
- [scripts/examples/circle_packing.py](scripts/examples/circle_packing.py) — the verified seed program, n=26 circles in a unit square, maximize summed radii. The canonical AlphaEvolve problem, use it to smoke-test your setup.
- [requirements.txt](requirements.txt) — the pip-installable deps for `evolve.py` (the `alpha_evolve` library installs separately from the repo above).

## Documentation Pages

You MUST fetch the matching page below before writing code against AlphaEvolve. These hosted docs are the source of truth for parameters, provisioning, and edge cases, do not rely solely on the examples above.

- Overview, https://docs.cloud.google.com/gemini/enterprise/docs/alphaevolve/developer-guide/overview
- Install and configure, https://docs.cloud.google.com/gemini/enterprise/docs/alphaevolve/developer-guide/get-started
- The client library and examples, https://github.com/Google-Cloud-AI/alphaevolve-on-googlecloud

## From the episode

Built live on the Friday stream, AlphaEvolve is live, run DeepMind's evolutionary coding agent on your own code. Video link to follow.
