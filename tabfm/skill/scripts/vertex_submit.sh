#!/usr/bin/env bash
# Submit TabFM as a Vertex AI custom training job on a GPU.
#
#   ./vertex_submit.sh YOUR_PROJECT_ID [REGION]
#
# Defaults to one NVIDIA L4 on g2-standard-8 in us-central1. The job uses a
# prebuilt PyTorch GPU container, installs tabfm from GitHub at startup
# (the PyPI package cannot load the published weights), pulls the task
# script from this repo, and streams the result to the job logs.
set -euo pipefail

PROJECT="${1:?usage: vertex_submit.sh PROJECT_ID [REGION]}"
REGION="${2:-us-central1}"
IMAGE="us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-4.py310:latest"
RAW="https://raw.githubusercontent.com/SaschaHeyer/gen-ai-livestream/main/tabfm/skill/scripts/vertex_task.py"

RUN_CMD="pip install --quiet 'tabfm[pytorch] @ git+https://github.com/google-research/tabfm' scikit-learn && curl -sL $RAW -o /tmp/vertex_task.py && HF_HUB_DISABLE_XET=1 python /tmp/vertex_task.py"

gcloud ai custom-jobs create \
  --project="$PROJECT" \
  --region="$REGION" \
  --display-name="tabfm-gpu-demo" \
  --worker-pool-spec=replica-count=1,machine-type=g2-standard-8,accelerator-type=NVIDIA_L4,accelerator-count=1,container-image-uri="$IMAGE" \
  --command=bash,-c \
  --args="$RUN_CMD"

echo ""
echo "Stream the logs with:"
echo "  gcloud ai custom-jobs stream-logs JOB_ID --project=$PROJECT --region=$REGION"
