# TabFM, tested honestly

Zero-shot tabular prediction with Google's TabFM, benchmarked honestly against XGBoost and TabICL on the same data and the same split. Everything here ran end to end before it was published.

From the Friday livestream. [EPISODE VIDEO LINK]

Original announcement, https://research.google/blog/introducing-tabfm-a-zero-shot-foundation-model-for-tabular-data/

## Setup

Python 3.11 or newer is required.

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r skill/requirements.txt

# the default Hugging Face Xet download backend can crash mid-download,
# plain HTTP is reliable
export HF_HUB_DISABLE_XET=1
```

Install from the requirements file as is. It pins `tabfm` to the GitHub repo on purpose, the PyPI 1.0.0 package cannot load the published weights (its loader wants `pytorch_model.bin`, the Hugging Face repo ships `model.safetensors`).

The classification checkpoint is 6.6 GB and downloads from Hugging Face on the first `load()` call. Budget disk and a few minutes.

## The scripts

They live in `skill/scripts/` so they ship as supporting files with the installable agent skill, one folder, one source of truth.

- `skill/scripts/demo.py` zero-shot classification in six lines, fit stashes your table as context, predict is a single forward pass. Measured here, accuracy 1.0000 on wine, model load 7.6s warm, fit plus predict 49s on CPU.
- `skill/scripts/race.py` the honest benchmark, TabFM vs XGBoost vs TabICL, same split, accuracy, time, and checkpoint size side by side. Each model runs in its own subprocess, XGBoost and PyTorch both bring their own OpenMP runtime on macOS and crash or deadlock inside one process.
- `skill/scripts/limit-test.py` proves the 10-class hard cap first hand, an 11-class fit raises `ValueError: The number of classes (11) exceeds the maximum number of classes (10) supported by the model.`

## Install the agent skill

```bash
npx skills add https://github.com/SaschaHeyer/gen-ai-livestream/tree/main/tabfm/skill
```

Your agent gets the verified setup, all the sharp edges below, and the runnable scripts.

## Sharp edges to know

- On CPU pass `dtype=torch.float32` to `load()`. The bfloat16 default ran ~4.5x slower on CPU in testing (220s vs 49s).
- `predict()` returns labels in an object-dtype array, cast before handing it to sklearn metrics.
- Hard limits, 10 classes max, optimized up to 500 features, and every training row rides along as context so memory grows with your table.
- The code is Apache 2.0 but the weights carry the TabFM Non-Commercial License v1.0, read it before building a product on them.
- The announced BigQuery SQL integration is not shipped yet.

## The result

On wine, all three models tie at accuracy 1.0000. TabFM pays 55 seconds and a 6.6 GB checkpoint for it, TabICL 2.5 seconds and 0.11 GB, XGBoost 0.4 seconds. The takeaway is not that TabFM is bad, it is that a leaderboard number is not your data. Benchmark on your own table before you swap anything out.
