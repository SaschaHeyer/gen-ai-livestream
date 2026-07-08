---
name: tabfm
description: Use this skill when working with TabFM, Google's zero-shot tabular foundation model, running classification or regression on a CSV or DataFrame without training, benchmarking TabFM against XGBoost or TabICL, or debugging TabFM installation and weight loading. Covers the tabfm Python package, TabFMClassifier and TabFMRegressor, Hugging Face weight download, the PyPI loader bug, CPU dtype performance, hard model limits, and the weight license.
---

# TabFM Skill

Zero-shot prediction on tabular data with Google's TabFM, the scikit-learn compatible foundation model that reads your whole table as context and predicts in a single forward pass, no training, no tuning, no feature engineering.

> [!IMPORTANT]
> Install from the GitHub repo, `pip install "tabfm[pytorch] @ git+https://github.com/google-research/tabfm"`. Python 3.11 or newer, and the `[pytorch]` extra is required, without it no backend is installed at all.

> [!WARNING]
> Do NOT `pip install tabfm` from PyPI. PyPI 1.0.0 is stale and cannot load the published weights, its loader looks for `classification/pytorch_model.bin` while the Hugging Face repo `google/tabfm-1.0.0-pytorch` ships `model.safetensors`, so `load()` dies with FileNotFoundError. The GitHub package loads safetensors natively and downloads only the checkpoint it needs (6.6 GB instead of the full 13.1 GB).

> [!WARNING]
> The word open has an asterisk. The GitHub code is Apache 2.0, but the model weights carry the TabFM Non-Commercial License v1.0. Do not build a commercial product on the weights without reading that license.

> [!WARNING]
> The announced BigQuery SQL integration is upcoming, not shipped. Do not plan a `SELECT` against TabFM today.

---

## Dependencies and Prerequisites

- **Python >= 3.11** (3.12 verified). This floor is hard, the tabfm package refuses older interpreters, and Google's own prebuilt Vertex training containers ship 3.10 and cannot run it.
- **Packages**, install the pinned set with `pip install -r requirements.txt`, or minimally `pip install "tabfm[pytorch] @ git+https://github.com/google-research/tabfm" safetensors scikit-learn pandas xgboost tabicl`. The `[pytorch]` extra and the explicit `safetensors` are both required, see the warnings above.
- **No system binaries needed.** CPU works for small tables, a CUDA GPU makes inference ~14x faster (see the GPU section).
- **Disk**, the classification checkpoint is 6.6 GB, downloaded from Hugging Face on first `load()`.

## Quick Start

Verified end to end on 2026-07-07, CPU only, no GPU.

```bash
# Python >= 3.11 required (3.12 verified)
uv venv --python 3.12 .venv
uv pip install "tabfm[pytorch] @ git+https://github.com/google-research/tabfm" safetensors

# the default HF Xet download backend can crash mid-download
# (hf-xet Internal Writer Error), plain HTTP is reliable
export HF_HUB_DISABLE_XET=1
```

> [!WARNING]
> `safetensors` must be installed explicitly. tabfm does not declare it as a dependency but its loader needs it, the published weights are safetensors-only. In a clean environment without it, `load()` fails with `NameError: name 'safetensors' is not defined` deep inside huggingface_hub, after the 6.6 GB download.

Zero-shot classification, the whole thing:

```python
import os
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
import torch
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

from tabfm.src.pytorch import tabfm_v1_0_0
from tabfm import TabFMClassifier

X, y = load_wine(return_X_y=True, as_frame=True)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, stratify=y)

model = tabfm_v1_0_0.load(dtype=torch.float32)   # see dtype warning below
clf = TabFMClassifier(model=model)
clf.fit(X_train, y_train)            # no training, stashes the table as context
preds = clf.predict(X_test)          # single forward pass
print(accuracy_score(y_test, preds.astype(int)))
```

> [!WARNING]
> On CPU pass `dtype=torch.float32` to `load()`. The loader defaults to bfloat16, which ran ~4.5x slower on CPU in testing (220s vs 49s for the same fit and predict). Keep the bfloat16 default on GPU.

> [!WARNING]
> `predict()` returns the original class labels in an object-dtype numpy array. sklearn metrics refuse the mix, cast first (`preds.astype(int)` for integer labels, or compare as strings).

Measured on the wine dataset (178 rows, 13 features, 3 classes), model load 7.6s warm, fit plus predict 49.2s on CPU, accuracy 1.0000.

## Workflow, benchmark the user's own data

The headline utility is [scripts/benchmark.py](scripts/benchmark.py), it runs TabFM, XGBoost, and TabICL on any CSV with the same split and prints accuracy, time, and context size side by side.

1. **Check the data first.** Classification only, at most 10 classes in the target column (the script refuses more, before the 6.6 GB model loads), a warning above 500 features.
2. **Run it.**
   ```bash
   ./scripts/benchmark.py data.csv --target label
   ./scripts/benchmark.py data.csv --target label --models xgboost,tabfm --max-context 500
   ```
   Context above `--max-context` (default 1,000) is deduplicated and stratified-sampled for the zero-shot models, every context row costs TabFM memory and time (1,000 rows measured at ~13 minutes on CPU).
3. **Report the table back**, and the honest reading, a tie means the smaller model already does the job, and one split is one draw, rerun with another `--seed` before deciding anything.

## The honest benchmark result

Same data, same split, TabFM vs the classics. On the wine dataset all three tied at accuracy 1.0000, and the costs were not close, XGBoost 0.4s with a megabyte-scale model, TabICL 2.5s with 0.11 GB, TabFM 55.0s with a 6.6 GB checkpoint (13.1 GB on disk when both classification and regression are fetched, which is what broken PyPI installs do). On a Vertex AI NVIDIA L4 the same TabFM fit plus predict drops to 3.6s (verified, see the GPU section), which closes most of the gap yet still leaves CPU XGBoost 9x faster at zero hardware cost. When recommending a model, benchmark on the user's own data first, and when a classic ties TabFM there, prefer the classic, it is orders of magnitude cheaper to run and deploy.

> [!WARNING]
> Never import xgboost and tabfm in the same Python process on macOS. Both bundle their own OpenMP runtime and the process segfaults or silently deadlocks at 0 percent CPU. Run each model in its own subprocess when comparing, [scripts/race.py](scripts/race.py) shows the pattern. `KMP_DUPLICATE_LIB_OK=TRUE` does NOT fix it.

## Determinism

TabFM predictions are fully reproducible by default. Measured, 10 full fit and predict retries produced byte-identical outputs, and 10 further runs with different `random_state` values produced zero prediction flips across the test set. The mechanism, prediction is a 32-member ensemble averaged and argmaxed, not generative sampling, and the sklearn wrapper pins `random_state=42`. Borderline rows on harder data are where different seeds could flip a prediction.

## Hard limits

From the model card and the classifier defaults, confirmed against the installed package.

- Classification supports at most 10 classes, a hard architectural limit. Confirmed in code, an 11-class fit raises the ValueError.
- Optimized for up to 500 features (`max_num_features=500` default).
- Every training row is passed as context at inference, memory AND latency scale with your table. Measured on CPU, 124 context rows took 49s for fit plus predict, 1,000 rows took 13.3 minutes, 5,000 rows exceeded 30 minutes. For anything beyond a few hundred context rows plan for a GPU, or deduplicate and subsample the context.
- Dedup plus stratified subsampling works. On a synthetic 1M-row table with 90 percent duplicate rows, 1,000 deduplicated context rows matched an XGBoost trained on the full 800,000, measured across two rounds. Do not feed a large table raw, sample it.
- Regression uses `TabFMRegressor` with the separate regression checkpoint (6.59 GB), not verified here.

## Run it on a cloud GPU

The CPU numbers above are the reason, beyond a few hundred context rows CPU inference takes minutes to hours. Verified on a Vertex AI NVIDIA L4, the same wine fit plus predict took 3.6s vs 49.2s on CPU, roughly 14x, and the bfloat16 default is correct on GPU. For provisioning (one L4, one command), load [vertex-ai.md](vertex-ai.md), it has the submit script, the measured numbers, and three verified cloud traps, Google's prebuilt training containers ship Python 3.10 which tabfm rejects, a job that cannot see the GPU driver succeeds silently on CPU while billing the GPU, and L4 capacity starves by region and hour.

## Supporting files

These ship with the skill and are the verified reference implementations, run them rather than rewriting from scratch.

- [scripts/benchmark.py](scripts/benchmark.py) THE HEADLINE UTILITY, the honest benchmark on any CSV, guardrails built in, each model in its own subprocess (XGBoost and PyTorch load conflicting OpenMP runtimes on macOS, one process segfaults)
  `./scripts/benchmark.py data.csv --target label`
- [requirements.txt](requirements.txt) pinned to the exact versions that ran, installs tabfm from GitHub on purpose
  `pip install -r requirements.txt`
- [vertex-ai.md](vertex-ai.md) run TabFM on a Vertex AI GPU, load when someone wants cloud provisioning
- [scripts/demo.py](scripts/demo.py) the episode's verified zero-shot demo on wine, the Quick Start as a runnable file
  `python scripts/demo.py`
- [scripts/race.py](scripts/race.py) the episode's frozen three-way benchmark on wine, the reproduction behind the published numbers
  `python scripts/race.py`
- [scripts/limit-test.py](scripts/limit-test.py) proves the 10-class cap, an 11-class fit raises the documented ValueError
  `python scripts/limit-test.py`
- [scripts/determinism.py](scripts/determinism.py) proves predictions are reproducible, 10 retries byte-identical, 10 seeds zero flips
  `python scripts/determinism.py`
- [scripts/vertex_task.py](scripts/vertex_task.py) the task that runs inside the Vertex AI job, GPU aware, fails loudly on silent CPU fallback
- [scripts/vertex_submit.sh](scripts/vertex_submit.sh) one-command Vertex AI job submission, L4 default
  `./scripts/vertex_submit.sh YOUR_PROJECT_ID europe-west4`

## Documentation Pages

You MUST fetch the matching page below before writing code. These hosted pages are the source of truth for parameters, limits, and the license, do not rely solely on the examples above.

- https://github.com/google-research/tabfm
- https://huggingface.co/google/tabfm-1.0.0-pytorch
- https://research.google/blog/introducing-tabfm-a-zero-shot-foundation-model-for-tabular-data/

## From the episode

Built live on the Friday stream. [EPISODE VIDEO LINK]
