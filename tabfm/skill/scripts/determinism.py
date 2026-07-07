"""Dirk's question, how deterministic is TabFM across retries.
Part 1, 10 full fit+predict retries with the default seed.
Part 2, 10 runs with different random_state values.
"""
import os, time, hashlib, itertools
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
import torch
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from tabfm.src.pytorch import tabfm_v1_0_0
from tabfm import TabFMClassifier

X, y = load_wine(return_X_y=True, as_frame=True)
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
model = tabfm_v1_0_0.load(dtype=torch.float32)

def run(seed):
    clf = TabFMClassifier(model=model, random_state=seed)
    clf.fit(Xtr, ytr)
    return clf.predict(Xte).astype(int)

print("== part 1, 10 retries, default seed 42 ==", flush=True)
base = None
for i in range(10):
    t0 = time.time()
    p = run(42)
    h = hashlib.md5(p.tobytes()).hexdigest()[:8]
    if base is None:
        base = p
    print(f"retry {i+1:2d}: identical_to_first={bool((p == base).all())} "
          f"hash={h} acc={accuracy_score(yte, p):.4f} ({time.time()-t0:.0f}s)", flush=True)

print("== part 2, 10 different seeds ==", flush=True)
runs = [base]
for seed in range(10):
    p = run(seed)
    runs.append(p)
    flips = int((p != base).sum())
    print(f"seed {seed}: flips_vs_seed42={flips}/{len(base)} "
          f"acc={accuracy_score(yte, p):.4f}", flush=True)

maxdis = max(int((a != b).sum()) for a, b in itertools.combinations(runs, 2))
print(f"RESULT max pairwise disagreement across all 11 runs: {maxdis}/{len(base)} test rows", flush=True)
