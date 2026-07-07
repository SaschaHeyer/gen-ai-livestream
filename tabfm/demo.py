import os, time
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")   # default Xet download backend can crash, plain HTTP is reliable
import torch
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

from tabfm.src.pytorch import tabfm_v1_0_0
from tabfm import TabFMClassifier

X, y = load_wine(return_X_y=True, as_frame=True)
print(f"dataset: wine, {X.shape[0]} rows, {X.shape[1]} features, {y.nunique()} classes")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, stratify=y)

t0 = time.time()
# dtype=float32 on CPU, the bfloat16 default is ~4.5x slower there
model = tabfm_v1_0_0.load(dtype=torch.float32)
print(f"model load: {time.time()-t0:.1f}s")

clf = TabFMClassifier(model=model)
t1 = time.time()
clf.fit(X_train, y_train)                # no training, stashes the table as context
preds = clf.predict(X_test)              # single forward pass
print(f"fit+predict: {time.time()-t1:.1f}s")

# predict() returns original labels in an object-dtype array, cast before scoring
print(f"TabFM zero-shot accuracy: {accuracy_score(y_test, preds.astype(int)):.4f}")
