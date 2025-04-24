  ````
  gcloud builds submit --tag gcr.io/sascha-playground-doit/cloud-run-gpus                                               
  ````
  
  ````
  gcloud beta run deploy cloud-run-gpus \
    --image gcr.io/sascha-playground-doit/cloud-run-gpus \
    --cpu 4 \
    --memory 16Gi \
    --no-cpu-throttling \
    --gpu 1 \
    --gpu-type nvidia-l4 \
    --max-instances 
````