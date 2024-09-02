## Usage

replace `sascha-playground-doit` with your project ID

````
gcloud builds submit --tag gcr.io/sascha-playground-doit/document-understanding

gcloud run deploy --image gcr.io/sascha-playground-doit/document-understanding --platform managed --allow-unauthenticated

````