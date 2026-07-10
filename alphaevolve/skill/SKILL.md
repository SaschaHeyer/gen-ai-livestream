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

The command above smoke-tests your setup on Google's circle packing sample. The real showcase is [examples/camera-background-blur](../examples/camera-background-blur), the flagship experiment from the episode.

**Flagship result, a real webcam background blur made faster.** The seed is production code from Stage Studio, a native macOS streaming app, the per-frame person-segmentation-plus-blur that ran the webcam compositor. AlphaEvolve made it **3.4x faster with visually identical output** (17.95 ms to 5.26 ms per frame, SSIM 0.998 versus the original), in a single run of 10 candidates, judged entirely by an automated evaluator, no human in the loop. It evolves **Swift**, compiled with `swiftc` and scored locally, which works because evaluation is fully client-side, any language you can compile and score works.

> [!IMPORTANT]
> **AlphaEvolve never sees your output, only the numbers your evaluator returns.** So the metric must be ungameable. The blur experiment scores `speedup` but gates it behind an SSIM floor, any candidate below SSIM 0.98 mean or 0.95 on its worst frame gets the failure sentinel instead of a speedup. Quality is a rule, not a tradeoff, the only way to score is to look identical and be faster. If your metric has a loophole, evolution finds the loophole, not the optimization.

> [!WARNING]
> **Progress is non-monotonic, do not stop early.** The best score plateaus and jumps, and an early candidate can score worse than the seed before the run climbs past it. A backward step is not a stuck run.

> [!WARNING]
> **Invalid candidates are a signal, not an error.** A candidate that breaks a constraint, fails to compile, or falls below the quality gate comes back with the sentinel score `-1e12` (a big negative number, not `-inf`, the API needs a real number), plus an insight string so the evolver learns why it died, a compile error versus a gate failure, not just that it died.

> [!WARNING]
> **The backend can finish before it hits your budget.** The controller loop stops itself after 120 seconds with no new candidates and an empty queue. Treat the budget as a ceiling, not a guarantee, a run can finish a candidate or two short.

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
- [scripts/examples/circle_packing.py](scripts/examples/circle_packing.py) — Google's circle packing sample (n=26, maximize summed radii), a simple Python example to smoke-test your setup.
- [../examples/camera-background-blur](../examples/camera-background-blur) — the flagship experiment, evolve a real macOS webcam blur to run 3.4x faster with identical output. Its own seed (Swift), evaluator (speedup gated by SSIM), bench harness, and the winning program. Read this one to see how a real, ungameable objective is built.
- [requirements.txt](requirements.txt) — the pip-installable deps for `evolve.py` (the `alpha_evolve` library installs separately from the repo above).

## Documentation Pages

You MUST fetch the matching page below before writing code against AlphaEvolve. These hosted docs are the source of truth for parameters, provisioning, and edge cases, do not rely solely on the examples above.

- Overview, https://docs.cloud.google.com/gemini/enterprise/docs/alphaevolve/developer-guide/overview
- Install and configure, https://docs.cloud.google.com/gemini/enterprise/docs/alphaevolve/developer-guide/get-started
- The client library and examples, https://github.com/Google-Cloud-AI/alphaevolve-on-googlecloud

## From the episode

Built live on the Friday stream, we made a real webcam background blur 3.4x faster with AlphaEvolve, on the actual production code from a shipping macOS app. Video link to follow.
