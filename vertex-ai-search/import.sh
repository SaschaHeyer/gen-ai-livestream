#!/bin/bash

# Set your Project ID and media data store
export PROJECT_ID=${PROJECT_ID:-sascha-playground-doit}
export DATA_STORE_ID=${DATA_STORE_ID:-media-workshop}
export LOCATION=${LOCATION:-global}

echo "Project ID: $PROJECT_ID"
echo "Data Store ID: $DATA_STORE_ID"

# 1. Upload data to GCS (Optional if you want to use GCS import mode)
# echo "Uploading data to GCS..."
# gcloud storage buckets create gs://${PROJECT_ID}-media-demo --location=$LOCATION || true
# gcloud storage cp data/media_data.jsonl gs://${PROJECT_ID}-media-demo/media_data.jsonl

# 2. Run Ingestion Script (Direct Upload Mode for simplicity)
echo "Running ingestion script..."
/Users/sascha/Desktop/development/gen-ai-livestream/.venv/bin/python scripts/ingest_data.py \
  --project-id $PROJECT_ID \
  --location $LOCATION \
  --data-store-id $DATA_STORE_ID \
  --local-file data/media_data.jsonl

echo "Done."
