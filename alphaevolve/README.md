# AlphaEvolve on Google Cloud

Run DeepMind's Gemini-powered evolutionary coding agent on your own code. You give it a seed function and a scoring function, it evolves generations of variants and hands back one that beats your baseline.

From the Friday stream, we made a real webcam background blur 3.4x faster with AlphaEvolve.

## The flagship experiment

[examples/camera-background-blur](examples/camera-background-blur) is the complete, reproducible experiment from the episode. The seed is production code from [Stage Studio](https://stagestudio.tv), a native macOS streaming app, the per-frame person-segmentation-plus-blur on the webcam. AlphaEvolve made it **3.4x faster with visually identical output** (17.95 ms to 5.26 ms per frame, SSIM 0.998), in a single run of 10 candidates, judged entirely by an automated evaluator, no human in the loop.

The lesson it teaches best, AlphaEvolve never sees your output, only the numbers your evaluator returns, so the metric must be ungameable. Here the speedup is gated behind an SSIM floor, the only way to score is to look identical and be faster.

## What is here

- [examples/camera-background-blur](examples/camera-background-blur) — the flagship, evolve a Swift webcam blur, scored by speedup gated on visual identity.
- [skill/](skill/) — the installable skill. Point `skill/scripts/evolve.py` at any function with `EVOLVE-BLOCK` markers and an `evaluate()`, it drives the full AlphaEvolve loop and returns the best program. Start with `skill/SKILL.md`.

## The one command

The generic utility runs any Python program you can score. This smoke-tests your setup on Google's circle packing sample.

```bash
gcloud auth application-default login
export PROJECT_ID=your-project GE_APP_ID=your-gemini-enterprise-engine-id

python skill/scripts/evolve.py \
  --program skill/scripts/examples/circle_packing.py \
  --metric sum_of_radii --inputs '{"n": 26}' --max-programs 20
```

The camera-background-blur experiment evolves Swift instead, with its own evaluator that compiles each candidate and scores it, see that folder's README.

## Requires

A Google Cloud project with a Gemini Enterprise license (any tier, including a trial) and Discovery Engine enabled. See `skill/SKILL.md` for full prerequisites and the sharp edges.
