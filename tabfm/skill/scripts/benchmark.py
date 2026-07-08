#!/usr/bin/env python3
"""The honest benchmark, on YOUR data.

Runs TabFM, XGBoost, and TabICL on the same CSV with the same split and
prints accuracy, time, and notes side by side.

  ./benchmark.py data.csv --target label
  ./benchmark.py data.csv --target label --models tabfm,xgboost
  ./benchmark.py data.csv --target label --max-context 500 --test-size 0.2

Guardrails built in, classification only, at most 10 classes (TabFM's hard
cap, checked before the 6.6 GB model loads), a warning above 500 features,
and context capping with dedup plus stratified sampling for the zero-shot
models (every context row costs TabFM memory and time, 1,000 rows measured
at ~13 minutes on CPU).

Each model runs in its own subprocess, XGBoost and PyTorch bundle
conflicting OpenMP runtimes on macOS and crash or deadlock in one process.
"""
import argparse, json, os, subprocess, sys, time
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

CHILD = r'''
import json, os, sys, time
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

cfg = json.loads(sys.argv[1])
df = pd.read_csv(cfg["csv"])
y_raw = df[cfg["target"]]
X = df.drop(columns=[cfg["target"]])

# uniform, deterministic encoding so every model sees identical data
classes = sorted(y_raw.astype(str).unique())
y = y_raw.astype(str).map({c: i for i, c in enumerate(classes)}).to_numpy()
for col in X.columns:
    if not pd.api.types.is_numeric_dtype(X[col]):
        X[col] = X[col].astype("category").cat.codes
X = X.to_numpy(dtype="float32")

X_tr, X_te, y_tr, y_te = train_test_split(
    X, y, test_size=cfg["test_size"], random_state=cfg["seed"], stratify=y)

def cap_context(Xa, ya, k, seed):
    if len(ya) <= k:
        return Xa, ya, False
    rng = np.random.default_rng(seed)
    seen, keep = set(), []
    for i in rng.permutation(len(ya)):
        b = Xa[i].tobytes()
        if b not in seen:
            seen.add(b); keep.append(i)
        if len(keep) >= 3 * k:
            break
    keep = np.array(keep)
    out = []
    n_cls = len(np.unique(ya[keep]))
    for c in np.unique(ya[keep]):
        ci = keep[ya[keep] == c]
        out.append(ci[: max(1, k // n_cls)])
    idx = np.concatenate(out)[:k]
    return Xa[idx], ya[idx], True

name = cfg["model"]
t0 = time.time()
capped = False
if name == "xgboost":
    from xgboost import XGBClassifier
    m = XGBClassifier(verbosity=0, tree_method="hist")
    m.fit(X_tr, y_tr); preds = m.predict(X_te); ctx = len(y_tr)
elif name == "tabicl":
    from tabicl import TabICLClassifier
    Xc, yc, capped = cap_context(X_tr, y_tr, cfg["max_context"], cfg["seed"])
    m = TabICLClassifier()
    m.fit(Xc, yc); preds = m.predict(X_te); ctx = len(yc)
elif name == "tabfm":
    import torch
    from tabfm.src.pytorch import tabfm_v1_0_0
    from tabfm import TabFMClassifier
    Xc, yc, capped = cap_context(X_tr, y_tr, cfg["max_context"], cfg["seed"])
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = tabfm_v1_0_0.load(**({} if device == "cuda" else {"dtype": torch.float32}))
    m = TabFMClassifier(model=model)
    m.fit(Xc, yc); preds = m.predict(X_te); ctx = len(yc)

if getattr(preds, "dtype", None) == object:
    preds = preds.astype(int)
print(json.dumps({
    "model": name, "acc": float(accuracy_score(y_te, preds)),
    "seconds": round(time.time() - t0, 1), "context_rows": int(ctx),
    "context_capped": bool(capped),
}))
'''

def main():
    ap = argparse.ArgumentParser(description="TabFM vs the classics, on your CSV")
    ap.add_argument("csv")
    ap.add_argument("--target", required=True, help="label column name")
    ap.add_argument("--models", default="xgboost,tabicl,tabfm",
                    help="comma separated subset of xgboost,tabicl,tabfm")
    ap.add_argument("--test-size", type=float, default=0.3)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-context", type=int, default=1000,
                    help="context cap for the zero-shot models, dedup + stratified sample")
    args = ap.parse_args()

    import pandas as pd
    df = pd.read_csv(args.csv)
    if args.target not in df.columns:
        sys.exit(f"target column '{args.target}' not in CSV, columns are {list(df.columns)[:20]}")
    n_classes = df[args.target].nunique()
    n_features = df.shape[1] - 1
    if n_classes > 10:
        sys.exit(f"{n_classes} classes, TabFM supports at most 10 (hard architectural limit), "
                 "reduce the label space or benchmark without tabfm via --models xgboost")
    if n_classes < 2:
        sys.exit("the target column has a single value, nothing to classify")
    if n_features > 500:
        print(f"WARNING: {n_features} features, TabFM is optimized for up to 500", flush=True)
    print(f"dataset: {os.path.basename(args.csv)}, {df.shape[0]} rows, "
          f"{n_features} features, {n_classes} classes", flush=True)

    results = []
    for name in [m.strip() for m in args.models.split(",") if m.strip()]:
        cfg = {"csv": args.csv, "target": args.target, "model": name,
               "test_size": args.test_size, "seed": args.seed,
               "max_context": args.max_context}
        print(f"running {name} in its own process...", flush=True)
        out = subprocess.run([sys.executable, "-c", CHILD, json.dumps(cfg)],
                             capture_output=True, text=True)
        lines = [l for l in out.stdout.strip().splitlines() if l.startswith("{")]
        if not lines:
            err = out.stderr.strip().splitlines()[-1] if out.stderr.strip() else "no output"
            print(f"  {name} FAILED: {err}", flush=True)
            continue
        results.append(json.loads(lines[-1]))

    if results:
        print(f"\n{'model':<10} {'accuracy':>9} {'seconds':>9} {'context':>9}")
        for r in results:
            cap = " (capped)" if r["context_capped"] else ""
            print(f"{r['model']:<10} {r['acc']:>9.4f} {r['seconds']:>9.1f} "
                  f"{r['context_rows']:>9}{cap}")
        print("\nA tie means the smaller model already does the job. "
              "This split is one draw, rerun with another --seed before deciding.")

if __name__ == "__main__":
    main()
