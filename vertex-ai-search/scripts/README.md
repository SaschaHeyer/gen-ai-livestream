# Data Ingestion for Vertex AI Media Search

This directory contains scripts to ingest data into Vertex AI Search.

## Prerequisites

1.  **GCP Project**: Ensure you have a Google Cloud Project.
2.  **Vertex AI Search**: Enable the "Vertex AI Search and Conversation API".
3.  **Data Store**: Create a Data Store in Vertex AI Search.
    *   Go to [Vertex AI Search Console](https://console.cloud.google.com/gen-app-builder).
    *   Create a new App -> Search.
    *   Turn on "Advanced features" if needed (for Media Search specifics).
    *   Create a Data Store (e.g., "Structured Data" or "Media" if available/preview).
    *   **Note**: For this demo, we are using a generic "Structured Data" approach which works well for media metadata.

## Usage

### 1. Setup Environment

```bash
pip install google-cloud-discoveryengine
gcloud auth application-default login
```

### 2. Run Ingestion Script

You can ingest data from a local file (slower, item-by-item) or GCS (recommended for large datasets).

**Option A: Local File (Good for testing)**

```bash
python scripts/ingest_data.py \
  --project-id YOUR_PROJECT_ID \
  --location global \
  --data-store-id YOUR_DATA_STORE_ID \
  --local-file data/media_data.jsonl
```

**Option B: GCS (Production)**

1.  Upload `data/media_data.jsonl` to a GCS bucket.
2.  Run the script:

```bash
python scripts/ingest_data.py \
  --project-id YOUR_PROJECT_ID \
  --location global \
  --data-store-id YOUR_DATA_STORE_ID \
  --gcs-uri gs://YOUR_BUCKET/media_data.jsonl
```
