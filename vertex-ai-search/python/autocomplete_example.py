#!/usr/bin/env python3
"""
Minimal Python autocomplete example (matches web-app settings).
"""

import sys
from google.cloud import discoveryengine_v1

PROJECT_ID = "sascha-playground-doit"
LOCATION = "global"
DATA_STORE_ID = "media_1763324268059"
QUERY = sys.argv[1] if len(sys.argv) > 1 else "mars"


def main():
    client = discoveryengine_v1.CompletionServiceClient()
    data_store = (
        f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection/"
        f"dataStores/{DATA_STORE_ID}"
    )

    request = discoveryengine_v1.CompleteQueryRequest(
        data_store=data_store,
        query=QUERY,
        query_model="document",  # matches web-app
    )

    response = client.complete_query(request=request)

    print(f"Autocomplete for: '{QUERY}'")
    if not response.query_suggestions:
        print(" (no suggestions returned)")
    for idx, suggestion in enumerate(response.query_suggestions):
        print(f" {idx+1}. {suggestion.suggestion}")


if __name__ == "__main__":
    main()
