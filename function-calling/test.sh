curl \
-X POST \
-H "Content-Type: application/json" \
-H "Authorization: Bearer $(gcloud auth print-access-token)" \
"https://europe-west4-aiplatform.googleapis.com/v1/projects/sascha-playground-doit/locations/europe-west4/publishers/google/models/${MODEL_ID}:streamGenerateContent" -d '@prompt.json'