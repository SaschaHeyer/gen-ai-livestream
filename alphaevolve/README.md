# AlphaEvolve on Google Cloud

Run DeepMind's Gemini-powered evolutionary coding agent on your own code. You give it a seed function and a scoring function, it evolves generations of variants and hands back one that beats your baseline.

From the Friday stream, AlphaEvolve is live, run DeepMind's evolutionary coding agent on your own code.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/SaschaHeyer/gen-ai-livestream/blob/main/alphaevolve/notebook.ipynb)

Run the whole episode yourself in [notebook.ipynb](notebook.ipynb), the real circle packing evolution with your own Gemini Enterprise engine, plus two your-turn exercises.

## What is here

- [skill/](skill/) — the installable skill. Point `skill/scripts/evolve.py` at any function with `EVOLVE-BLOCK` markers and an `evaluate()`, it drives the full AlphaEvolve loop and returns the best program. Start with `skill/SKILL.md`.

## The one command

```bash
gcloud auth application-default login
export PROJECT_ID=your-project GE_APP_ID=your-gemini-enterprise-engine-id

python skill/scripts/evolve.py \
  --program skill/scripts/examples/circle_packing.py \
  --metric sum_of_radii --inputs '{"n": 26}' --max-programs 20
```

On a real n=26 circle packing run, the naive seed scores `sum_of_radii = 0.9415` and the best evolved program scores `2.6294`, a 2.79x improvement, in about 7.5 minutes.

## Requires

A Google Cloud project with a Gemini Enterprise license (any tier, including a trial) and Discovery Engine enabled. See `skill/SKILL.md` for full prerequisites and the sharp edges.
