set your variables within the .env file by renaming .env.sample to .env. 
After that you can deploy this cloud run service run `gcloud builds submit .`
this provide you with an API which needs to be set on the slack bot configuration as event webhook endpoint. 