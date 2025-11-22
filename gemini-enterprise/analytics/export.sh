curl -X POST \
-H "Authorization: Bearer $(gcloud auth print-access-token)" \
-H "Content-Type: application/json" \
-H "X-Goog-User-Project: sascha-playground-doit" \
-d '{
   "analytics": "projects/sascha-playground-doit/locations/LOCATION/collections/default_collection/engines/gemini-enterprise",
   "outputConfig":
      {
         "bigqueryDestination":
         {
            "datasetId": "gemini_analytics",
            "tableId": "metrics_2025_11_18"
         }
      }
   }' \
"https://discoveryengine.googleapis.com/v1alpha/projects/sascha-playground-doit/locations/global/collections/default_collection/engines/gemini-enterprise/analytics:exportMetrics"
