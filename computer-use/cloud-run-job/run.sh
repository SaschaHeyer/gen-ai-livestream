#!/usr/bin/env bash

set -euo pipefail

gcloud run jobs execute automation-job \
  --region us-central1 \
  --args="--target-url=https://browser-use-demo-24173060393.us-central1.run.app/" \
  --args="--pdf-uri=gs://yourbucket/sample.pdf" \
  --args="--note-text=test"
