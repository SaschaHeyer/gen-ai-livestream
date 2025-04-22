curl \
    -H "Authorization: Bearer $(gcloud auth print-access-token)" \
    -H "Content-Type: application/json" \
    https://us-central1-aiplatform.googleapis.com/v1beta1/projects/sascha-playground-doit/locations/us-central1/reasoningEngines/7069393573669502976/sessions/3908047504918183936
