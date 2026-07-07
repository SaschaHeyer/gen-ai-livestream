#!/usr/bin/env bash
# Submit TabFM as a Vertex AI custom training job on a GPU.
#
#   ./vertex_submit.sh YOUR_PROJECT_ID [REGION]
#
# Defaults to one NVIDIA L4 on g2-standard-8 in us-central1.
#
# The base image is python:3.12-slim ON PURPOSE. Google's prebuilt Vertex
# training containers (pytorch-gpu.2-4 and older) all ship Python 3.10,
# and tabfm requires >= 3.11, a prebuilt-container job fails with
# "Package 'tabfm' requires a different Python". pip installs the CUDA
# torch wheel, Vertex injects the GPU driver.
#
# tabfm installs from the GitHub TARBALL (not git+) because slim images
# carry no git, and the PyPI package cannot load the published weights.
# The whole run command contains no commas, gcloud --args splits on them.
set -euo pipefail

PROJECT="${1:?usage: vertex_submit.sh PROJECT_ID [REGION]}"
REGION="${2:-us-central1}"
IMAGE="python:3.12-slim"
RAW="https://raw.githubusercontent.com/SaschaHeyer/gen-ai-livestream/main/tabfm/skill/scripts/vertex_task.py"

# safetensors is listed explicitly, tabfm does not declare it but its loader
# needs it (the published weights are safetensors-only), a clean environment
# fails with "NameError: name 'safetensors' is not defined" without it
RUN_CMD="pip install --quiet 'tabfm[pytorch] @ https://github.com/google-research/tabfm/archive/refs/heads/main.tar.gz' safetensors scikit-learn && python -c \"import urllib.request as u; u.urlretrieve(*'$RAW /tmp/vertex_task.py'.split())\" && HF_HUB_DISABLE_XET=1 python /tmp/vertex_task.py"

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
