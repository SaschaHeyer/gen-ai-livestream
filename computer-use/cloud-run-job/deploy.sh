#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: deploy.sh [--skip-build] [--help] [-- gcloud-run-jobs-deploy-flags...]

Required environment variables:
  PROJECT_ID          Google Cloud project id.

Optional environment variables (with defaults):
  REGION              Cloud Run region (default: us-central1)
  JOB_NAME            Cloud Run Job name (default: automation-job)
  REPOSITORY          Artifact Registry repository (default: browser-use)
  IMAGE_TAG           Image tag pushed by Cloud Build (default: latest)

Flags:
  --skip-build        Skip the Cloud Build step and only run gcloud run jobs deploy.
  --help              Show this message and exit.
  --                  Everything after -- is passed directly to gcloud run jobs deploy.
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-us-central1}"
JOB_NAME="${JOB_NAME:-automation-job}"
REPOSITORY="${REPOSITORY:-browser-use}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "Error: PROJECT_ID environment variable must be set." >&2
  exit 1
fi

RUN_BUILD=true
DEPLOY_FLAGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-build)
      RUN_BUILD=false
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --)
      shift
      DEPLOY_FLAGS+=("$@")
      break
      ;;
    *)
      echo "Unknown flag: $1" >&2
      usage
      exit 1
      ;;
  esac
done

IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${JOB_NAME}:${IMAGE_TAG}"

pushd "${SCRIPT_DIR}" >/dev/null

if [[ "${RUN_BUILD}" == true ]]; then
  echo "Running Cloud Build for ${IMAGE}..."
  gcloud builds submit . \
    --config cloudbuild.yaml \
    --project "${PROJECT_ID}"
fi

echo "Deploying Cloud Run Job ${JOB_NAME}..."
gcloud run jobs deploy "${JOB_NAME}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  "${DEPLOY_FLAGS[@]}"

popd >/dev/null
