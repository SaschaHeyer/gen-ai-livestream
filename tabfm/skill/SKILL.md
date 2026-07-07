---
name: tabfm
description: Use this skill when working with TabFM, Google's zero-shot tabular foundation model, running classification or regression on a CSV or DataFrame without training, benchmarking TabFM against XGBoost or TabICL, or debugging TabFM installation and weight loading. Covers the tabfm Python package, TabFMClassifier and TabFMRegressor, Hugging Face weight download, the PyPI loader bug and its workarounds, hard model limits, and the weight license.
---

# TabFM Skill

Zero-shot prediction on tabular data with Google's TabFM, the scikit-learn compatible foundation model that reads your whole table as context and predicts in a single forward pass, no training, no tuning, no feature engineering.

> [!IMPORTANT]
> TabFM needs Python 3.11 or newer, and the install is `pip install "tabfm[pytorch]"`. The `[pytorch]` extra is required, plain `pip install tabfm` ships NO backend and imports will fail at load time.

> [!WARNING]
> PyPI `tabfm` 1.0.0 cannot load the published weights out of the box. Its loader looks for `classification/pytorch_model.bin`, but the Hugging Face repo `google/tabfm-1.0.0-pytorch` ships `model.safetensors`. Two ways out. Install the package from the GitHub repo instead (`google-research/tabfm`, its loader is safetensors native and downloads only the subfolder it needs), or keep the PyPI package and convert the weights once with the snippet in Quick Start below. The conversion path is the one verified end to end here.

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
uv pip install "tabfm[pytorch]" safetensors

# the default HF Xet download backend can crash mid-download
# (hf-xet Internal Writer Error), plain HTTP is reliable
export HF_HUB_DISABLE_XET=1
```

> [!WARNING]
> The full weight snapshot is 13.15 GB (classification 6.56 GB plus regression 6.59 GB) and the PyPI loader downloads all of it. Budget disk and one cold download of a few minutes. The GitHub version downloads only the subfolder it needs.

One-time weight conversion for the PyPI package (skip when installing from GitHub):

```python
import os, glob, torch
from safetensors.torch import load_file

snap = glob.glob(os.path.expanduser(
    "~/.cache/huggingface/hub/models--google--tabfm-1.0.0-pytorch/snapshots/*"))[0]
sd = load_file(os.path.join(snap, "classification", "model.safetensors"))
torch.save(sd, os.path.join(snap, "classification", "pytorch_model.bin"))
```

Zero-shot classification, the whole thing:

```python
import os
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

from tabfm.src.pytorch import tabfm_v1_0_0
from tabfm import TabFMClassifier

X, y = load_wine(return_X_y=True, as_frame=True)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, stratify=y)

model = tabfm_v1_0_0.load()          # pulls weights from the HF Hub on first call
clf = TabFMClassifier(model=model)
clf.fit(X_train, y_train)            # no training, stashes the table as context
preds = clf.predict(X_test)          # single forward pass
print(accuracy_score(y_test, preds.astype(int)))
```

> [!WARNING]
> `predict()` returns the original class labels in an object-dtype numpy array. sklearn metrics refuse the mix, cast first (`preds.astype(int)` for integer labels, or compare as strings).

Measured on the wine dataset (178 rows, 13 features, 3 classes), model load 10.7s warm, fit plus predict 44.5s on CPU, accuracy 1.0000.

## Hard limits

From the model card and the classifier defaults, confirmed against the installed package.

- Classification supports at most 10 classes, a hard architectural limit.
- Optimized for up to 500 features (`max_num_features=500` default).
- Every training row is passed as context at inference, memory scales with your table. Thousands of rows are fine on CPU, very large tables fall over.
- Regression uses `TabFMRegressor` with the separate regression checkpoint (another 6.59 GB).

## Documentation Pages

You MUST fetch the matching page below before writing code. These hosted pages are the source of truth for parameters, limits, and the license, do not rely solely on the examples above.

- https://github.com/google-research/tabfm
- https://huggingface.co/google/tabfm-1.0.0-pytorch
- https://research.google/blog/introducing-tabfm-a-zero-shot-foundation-model-for-tabular-data/

## From the episode

Built live on the Friday stream. [EPISODE VIDEO LINK]
