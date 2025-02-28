curl -X POST \
     -H "Authorization: Bearer $(gcloud auth print-access-token)" \
     -H "Content-Type: application/json; charset=utf-8" \
     -H "x-goog-user-project: sascha-playground-doit" \
     -d @request.json \
     "https://retail.googleapis.com/v2alpha/projects/sascha-playground-doit/locations/global/catalogs/default_catalog/userEvents:export"