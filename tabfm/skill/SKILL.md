---
name: tabfm
description: Use this skill when working with TabFM, Google's zero-shot tabular foundation model, running classification or regression on a CSV or DataFrame without training, benchmarking TabFM against XGBoost or TabICL, or debugging TabFM installation and weight loading. Covers the tabfm Python package, TabFMClassifier and TabFMRegressor, Hugging Face weight download, the PyPI loader bug, CPU dtype performance, hard model limits, and the weight license.
---

# TabFM Skill

Zero-shot prediction on tabular data with Google's TabFM, the scikit-learn compatible foundation model that reads your whole table as context and predicts in a single forward pass, no training, no tuning, no feature engineering.

> [!IMPORTANT]
> Install from the GitHub repo, `pip install "tabfm[pytorch] @ git+https://github.com/google-research/tabfm"`. Python 3.11 or newer, and the `[pytorch]` extra is required, without it no backend is installed at all.

> [!WARNING]
> Do NOT `pip install tabfm` from PyPI. PyPI 1.0.0 is stale and cannot load the published weights, its loader looks for `classification/pytorch_model.bin` while the Hugging Face repo `google/tabfm-1.0.0-pytorch` ships `model.safetensors`, so `load()` dies with FileNotFoundError. The GitHub package loads safetensors natively and downloads only the checkpoint it needs (6.6 GB instead of the full 13.2 GB).

> [!WARNING]
> The word open has an asterisk. The GitHub code is Apache 2.0, but the model weights carry the TabFM Non-Commercial License v1.0. Do not build a commercial product on the weights without reading that license.

> [!WARNING]
> The announced BigQuery SQL integration is upcoming, not shipped. Do not plan a `SELECT` against TabFM today.

---

## Quick Start

Verified end to end on 2026-07-07, CPU only, no GPU.

```bash
# Python >= 3.11 required (3.12 verified)
uv venv --python 3.12 .venv
uv pip install "tabfm[pytorch] @ git+https://github.com/google-research/tabfm"

# the default HF Xet download backend can crash mid-download
# (hf-xet Internal Writer Error), plain HTTP is reliable
export HF_HUB_DISABLE_XET=1
```

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

## Hard limits

From the model card and the classifier defaults, confirmed against the installed package.

- Classification supports at most 10 classes, a hard architectural limit.
- Optimized for up to 500 features (`max_num_features=500` default).
- Every training row is passed as context at inference, memory scales with your table. Thousands of rows are fine on CPU, very large tables fall over.
- Regression uses `TabFMRegressor` with the separate regression checkpoint (6.59 GB).

## Supporting files

These ship with the skill and are the verified reference implementations, run them rather than rewriting from scratch.

- [scripts/demo.py](scripts/demo.py) zero-shot classification end to end, the Quick Start as a runnable file
- [scripts/race.py](scripts/race.py) the honest benchmark, TabFM vs XGBoost vs TabICL on the same split, each model in its own subprocess (XGBoost and PyTorch load conflicting OpenMP runtimes on macOS, one process segfaults)
- [scripts/limit-test.py](scripts/limit-test.py) proves the 10-class cap, an 11-class fit raises the documented ValueError
- [scripts/requirements.txt](scripts/requirements.txt) pinned to the exact versions that ran, installs tabfm from GitHub on purpose

## Documentation Pages

You MUST fetch the matching page below before writing code. These hosted pages are the source of truth for parameters, limits, and the license, do not rely solely on the examples above.

- https://github.com/google-research/tabfm
- https://huggingface.co/google/tabfm-1.0.0-pytorch
- https://research.google/blog/introducing-tabfm-a-zero-shot-foundation-model-for-tabular-data/

## From the episode

Built live on the Friday stream. [EPISODE VIDEO LINK]
