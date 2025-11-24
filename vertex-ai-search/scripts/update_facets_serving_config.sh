#!/usr/bin/env bash

# Update Vertex AI Search serving config facetSpecs via REST.
# Requires: gcloud installed and logged in with access to the project.

set -euo pipefail

PROJECT_ID=${PROJECT_ID:-sascha-playground-doit}
LOCATION=${LOCATION:-global}
DATA_STORE_ID=${DATA_STORE_ID:-media_1763324268059}
SERVING_CONFIG_ID=${SERVING_CONFIG_ID:-default_search}

TOKEN=$(gcloud auth print-access-token)

PATCH_URL="https://discoveryengine.googleapis.com/v1beta/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/dataStores/${DATA_STORE_ID}/servingConfigs/${SERVING_CONFIG_ID}?updateMask=facetSpecs"

cat > /tmp/facet-specs.json <<'EOF'
{
  "facetSpecs": [
    {"facetKey": {"key": "categories_facet"}},
    {"facetKey": {"key": "content_type_facet"}},
    {"facetKey": {"key": "author_facet"}},
    {"facetKey": {"key": "language_facet"}},
    {"facetKey": {"key": "market_facet"}}
  ]
}
EOF

curl -X PATCH "${PATCH_URL}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  --data @/tmp/facet-specs.json

echo "\nDone: facetSpecs updated on ${SERVING_CONFIG_ID}."
