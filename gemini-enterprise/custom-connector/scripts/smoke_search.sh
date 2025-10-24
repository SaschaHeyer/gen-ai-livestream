#!/usr/bin/env bash
set -euo pipefail

PROJECT=${PROJECT:-sascha-playground-doit}
LOCATION=${LOCATION:-global}
DATA_STORE_ID=${DATA_STORE_ID:-demo_local_docs_acl_v1}
QUERY=${QUERY:-launch}
ACCESS_TOKEN=$(gcloud auth print-access-token)

curl -s -X POST \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT}" \
  "https://discoveryengine.googleapis.com/v1alpha/projects/${PROJECT}/locations/${LOCATION}/collections/default_collection/dataStores/${DATA_STORE_ID}/servingConfigs/default_search:search" \
  --data-binary @- <<JSON
{
  "query": "${QUERY}",
  "pageSize": 3,
  "contentSearchSpec": {
    "searchResultMode": "CHUNKS",
    "summarySpec": { "summaryResultCount": 1 }
  }
}
JSON
