# Vertex AI Media Search Workshop Assets

This repo has two parts:

- **Data + ingestion script** to load media/news content into a Vertex AI Media Search data store.
- **Next.js demo app (`web-app/`)** branded as a DoiT news + video portal that queries that data store with search, browse, facets, and sorting.

## 1) Prerequisites

- gcloud CLI authenticated to the workshop project `sascha-playground-doit`
- Python 3.10+ with `google-cloud-discoveryengine`
- Node 20+ for the Next.js app

```bash
cd /Users/sascha/Desktop/development/gen-ai-livestream/vertex-ai-search
python -m venv .venv && source .venv/bin/activate
pip install google-cloud-discoveryengine
cd web-app && npm install
```

## 2) Create a Media data store (one-time)

Follow the console workflow **Media → Data stores → Create data store → Media**. Note the **Data store ID** (use `media-workshop` to match defaults here) and keep it in `global` location. Then publish a Media app using that data store (App Builder → Create app (Media)).

## 3) Import the sample documents

```bash
cd /Users/sascha/Desktop/development/gen-ai-livestream/vertex-ai-search
export PROJECT_ID=sascha-playground-doit
export DATA_STORE_ID=media-workshop   # replace if you named it differently
./import.sh
```

The script loads `data/media_data.jsonl` with inline import (works for ≤100 docs). For bigger datasets set `--gcs-uri` to a JSONL in Cloud Storage.

## 4) Run the Next.js demo

```bash
cd /Users/sascha/Desktop/development/gen-ai-livestream/vertex-ai-search/web-app
cp .env.example .env.local
# edit values if your data store ID differs
npm run dev
```

Open `http://localhost:3000/search?q=ai` to see results with facets (categories, media_type) and sorting (relevance/newest).

## 5) Handy endpoints

- **Ingestion script**: `scripts/ingest_data.py` (inline or GCS import)
- **Sample data**: `data/media_data.jsonl`
- **Search API route**: `web-app/app/api/search/route.ts`
- **Preview search (CLI demo)**: `node scripts/preview_search.js --project-id sascha-playground-doit --data-store-id media_1763324268059 --location global --query "cloud"`
