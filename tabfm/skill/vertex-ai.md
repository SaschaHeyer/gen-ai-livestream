# TabFM on Vertex AI, GPU provisioning

Load this when someone wants to run TabFM on a cloud GPU instead of their laptop. The measured CPU scaling is the reason to bother, 124 context rows took 49s, 1,000 rows 13.3 minutes, 5,000 rows exceeded 30 minutes. Anything beyond a few hundred context rows wants a GPU.

> [!WARNING]
> This provisioning path is assembled from the current gcloud reference and has NOT yet been verified with a real job run. Verify the first run end to end before relying on it, and remove this warning once it has run clean.

## One-command submit

```bash
./scripts/vertex_submit.sh YOUR_PROJECT_ID us-central1
```

What it does, submits a Vertex AI custom job on one NVIDIA L4 (machine `g2-standard-8`), using Google's prebuilt PyTorch GPU training container. At startup the job installs tabfm from GitHub (the PyPI package cannot load the published weights, same trap as everywhere else), pulls [scripts/vertex_task.py](scripts/vertex_task.py) from this repo, and runs it with `HF_HUB_DISABLE_XET=1` set.

The underlying command, for adapting.

```bash
gcloud ai custom-jobs create \
  --project=PROJECT_ID \
  --region=us-central1 \
  --display-name="tabfm-gpu-demo" \
  --worker-pool-spec=replica-count=1,machine-type=g2-standard-8,accelerator-type=NVIDIA_L4,accelerator-count=1,container-image-uri=us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-4.py310:latest \
  --command=bash,-c \
  --args="pip install --quiet 'tabfm[pytorch] @ git+https://github.com/google-research/tabfm' scikit-learn && curl -sL https://raw.githubusercontent.com/SaschaHeyer/gen-ai-livestream/main/tabfm/skill/scripts/vertex_task.py -o /tmp/vertex_task.py && HF_HUB_DISABLE_XET=1 python /tmp/vertex_task.py"
```

Watch it run.

```bash
gcloud ai custom-jobs list --project=PROJECT_ID --region=us-central1
gcloud ai custom-jobs stream-logs JOB_ID --project=PROJECT_ID --region=us-central1
```

## Choices and why

- **GPU** `NVIDIA_L4` on `g2-standard-8` is the sensible default, modern, widely available, roughly a dollar an hour on demand (verify current pricing). Fallback when L4 quota is missing in a region, `NVIDIA_TESLA_T4` on `n1-standard-8`.
- **dtype** on GPU keep the loader's bfloat16 default, it is the fast path there. The `dtype=torch.float32` advice in SKILL.md is CPU-only.
- **Container** the prebuilt PyTorch GPU image provides CUDA and Python, the startup `pip install` brings tabfm's own pinned torch on top. First startup therefore spends a few minutes on install plus the 6.6 GB weight download, that is normal.
- **Weights cache** dies with the job. For repeated runs mount a GCS bucket via `--args` additions or bake a custom image, otherwise every job re-downloads 6.6 GB.
- **Quota** a fresh project has zero GPU quota in most regions, request `Custom model training Nvidia L4 GPUs` quota for the region first, that approval can take a day.

## Adapting the task

[scripts/vertex_task.py](scripts/vertex_task.py) runs the wine demo as a smoke test. For real data, replace the dataset load with a read from GCS (`pd.read_csv("gs://bucket/table.csv")` works inside the job) and keep the rest, the model limits from SKILL.md apply unchanged, 10 classes, 500 features, context rows cost memory.
