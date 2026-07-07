"""TabFM on a Vertex AI GPU, the task that runs inside the training job.

Expects tabfm[pytorch] to be installed already, the submit script does that.
On GPU the bfloat16 default is the right choice, the float32 advice in this
skill is CPU-only.
"""
import os, time
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
import torch
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

from tabfm.src.pytorch import tabfm_v1_0_0
from tabfm import TabFMClassifier

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"device: {device}"
      + (f" ({torch.cuda.get_device_name(0)})" if device == "cuda" else ""), flush=True)

X, y = load_wine(return_X_y=True, as_frame=True)
print(f"dataset: wine, {X.shape[0]} rows, {X.shape[1]} features, {y.nunique()} classes", flush=True)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, stratify=y)

t0 = time.time()
model = tabfm_v1_0_0.load(device=device)   # bf16 default, correct on GPU
print(f"model load: {time.time()-t0:.1f}s", flush=True)

clf = TabFMClassifier(model=model)
t1 = time.time()
clf.fit(X_train, y_train)
preds = clf.predict(X_test)
print(f"fit+predict: {time.time()-t1:.1f}s", flush=True)
print(f"TabFM zero-shot accuracy: {accuracy_score(y_test, preds.astype(int)):.4f}", flush=True)
