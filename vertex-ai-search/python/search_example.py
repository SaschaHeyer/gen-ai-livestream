#!/usr/bin/env python3
"""
Minimal Python example to call Vertex AI Search (Media) search API and print results + facets.
Based on: https://cloud.google.com/generative-ai-app-builder/docs/preview-search-results#genappbuilder_search-python
"""

import json
import sys
from google.cloud import discoveryengine_v1beta as discoveryengine

# Configure these
PROJECT_ID = "sascha-playground-doit"
LOCATION = "global"
DATA_STORE_ID = "media_1763324268059"
QUERY = sys.argv[1] if len(sys.argv) > 1 else ""
PAGE_SIZE = 10


def main():
    # serving config: default_search under the media data store
    serving_config = (
        f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection/"
        f"dataStores/{DATA_STORE_ID}/servingConfigs/default_search"
    )

    client = discoveryengine.SearchServiceClient()

    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=QUERY,
        page_size=PAGE_SIZE,
        facet_specs=[
            discoveryengine.SearchRequest.FacetSpec(
                facet_key=discoveryengine.SearchRequest.FacetSpec.FacetKey(key="categories"),
                limit=20,
            ),
            discoveryengine.SearchRequest.FacetSpec(
                facet_key=discoveryengine.SearchRequest.FacetSpec.FacetKey(key="content_type"),
                limit=10,
            ),
            discoveryengine.SearchRequest.FacetSpec(
                facet_key=discoveryengine.SearchRequest.FacetSpec.FacetKey(key="language_code"),
                limit=10,
            ),
            discoveryengine.SearchRequest.FacetSpec(
                facet_key=discoveryengine.SearchRequest.FacetSpec.FacetKey(key="author_facet"),
                limit=10,
            ),
            discoveryengine.SearchRequest.FacetSpec(
                facet_key=discoveryengine.SearchRequest.FacetSpec.FacetKey(key="market_facet"),
                limit=10,
            ),
        ],
    )

    response_iter = client.search(request=request)

    print(f"Query: '{QUERY}'")
    print("Results:")
    for idx, result in enumerate(response_iter):
        doc = result.document
        print(f" {idx+1:02d}. id={doc.id} title={doc.struct_data.get('title')}")
    # Collect facets from the last response page
    facets = getattr(response_iter, 'facets', None)
    if facets:
        print("\nFacets:")
        for facet in facets:
            print(f"- {facet.key}")
            for v in facet.values:
                print(f"   {v.value} ({v.count})")


if __name__ == "__main__":
    main()
