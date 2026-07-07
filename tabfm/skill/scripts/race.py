"""Three-way benchmark, TabFM vs XGBoost vs TabICL, same data, same split.

Each model runs in its OWN subprocess. XGBoost and PyTorch each bring their
own OpenMP runtime on macOS, and loading both in one process segfaults or
deadlocks. Process isolation avoids the fight entirely.
"""
import json, os, subprocess, sys

BENCH = r'''
import json, os, sys, time
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

X, y = load_wine(return_X_y=True, as_frame=True)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, stratify=y)

name = sys.argv[1]
t0 = time.time()
if name == "XGBoost":
    from xgboost import XGBClassifier
    m = XGBClassifier(verbosity=0)
    m.fit(X_train, y_train); preds = m.predict(X_test)
elif name == "TabICL":
    from tabicl import TabICLClassifier
    m = TabICLClassifier()
    m.fit(X_train, y_train); preds = m.predict(X_test)
elif name == "TabFM":
    import torch
    from tabfm.src.pytorch import tabfm_v1_0_0
    from tabfm import TabFMClassifier
    model = tabfm_v1_0_0.load(dtype=torch.float32)
    m = TabFMClassifier(model=model)
    m.fit(X_train, y_train); preds = m.predict(X_test)
dt = time.time() - t0
if getattr(preds, "dtype", None) == object:
    preds = preds.astype(int)
print(json.dumps({"name": name, "acc": accuracy_score(y_test, preds), "sec": dt}))
'''

results = {}
for name in ["XGBoost", "TabICL", "TabFM"]:
    print(f"running {name} in its own process...", flush=True)
    out = subprocess.run([sys.executable, "-c", BENCH, name],
                         capture_output=True, text=True)
    line = [l for l in out.stdout.strip().splitlines() if l.startswith("{")][-1]
    r = json.loads(line)
    results[name] = (r["acc"], r["sec"])
    print(f'{name:8s} accuracy={r["acc"]:.4f}  fit+predict={r["sec"]:.1f}s', flush=True)

import glob
def gb(pat):
    return sum(os.path.getsize(f) for f in glob.glob(os.path.expanduser(pat))
               if os.path.isfile(f) and not os.path.islink(f)) / 1e9

sizes = {
    "XGBoost": 0.001,
    "TabICL":  gb("~/.cache/huggingface/hub/models--jingang--TabICL/blobs/*"),
    "TabFM":   gb("~/.cache/huggingface/hub/models--google--tabfm-1.0.0-pytorch/blobs/*"),
}
print("checkpoint sizes GB:", {k: round(v, 3) for k, v in sizes.items()}, flush=True)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
names = list(results)
accs  = [results[n][0] for n in names]
times = [results[n][1] for n in names]
szs   = [max(sizes[n], 0.001) for n in names]
fig, axes = plt.subplots(1, 3, figsize=(12, 4))
for ax, vals, title, fmt in [
    (axes[0], accs,  "Accuracy (wine, same split)", "{:.3f}"),
    (axes[1], times, "Fit + predict seconds",       "{:.1f}s"),
    (axes[2], szs,   "Checkpoint size GB (log)",    "{:.3g}"),
]:
    bars = ax.bar(names, vals, color=["#6BA68C", "#8B82D6", "#D9734E"])
    ax.set_title(title)
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, b.get_height(), fmt.format(v), ha="center", va="bottom")
axes[2].set_yscale("log")
plt.tight_layout()
plt.savefig("beat3-race-chart.png", dpi=150)
print("chart saved: beat3-race-chart.png", flush=True)
