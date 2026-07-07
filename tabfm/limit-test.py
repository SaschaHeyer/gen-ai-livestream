import os
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
import numpy as np, torch
from tabfm.src.pytorch import tabfm_v1_0_0
from tabfm import TabFMClassifier

rng = np.random.default_rng(0)
X = rng.normal(size=(220, 5))
y = np.arange(220) % 11          # 11 classes, one past the documented cap
model = tabfm_v1_0_0.load(dtype=torch.float32)
clf = TabFMClassifier(model=model)
try:
    clf.fit(X, y)
    preds = clf.predict(X[:10])
    print("UNEXPECTED: 11 classes fit and predicted without error")
except Exception as e:
    print(f"CONFIRMED, 11 classes rejected: {type(e).__name__}: {str(e)[:200]}")
