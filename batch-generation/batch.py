import os
from vertexai.preview.batch_prediction import BatchPredictionJob
import vertexai
import time

def batch_generation(input_uri: str, output_uri: str):
    # Initialize Vertex AI with your project
    #vertexai.init(project="sascha-playground-doit", location="us-central1")
    
    # Submit the batch prediction job
    batch_prediction_job = BatchPredictionJob.submit(
        source_model="gemini-1.5-flash-002",  # Use the appropriate Gemini model
        input_dataset=input_uri,
        output_uri_prefix=output_uri,
    )
    
    # Monitor the job
    while not batch_prediction_job.has_ended:
        print(f"Job state: {batch_prediction_job.state.name}")
        time.sleep(5)
        batch_prediction_job.refresh()

    if batch_prediction_job.has_succeeded:
        print(f"Job succeeded! Output located at: {batch_prediction_job.output_location}")
    else:
        print(f"Job failed with error: {batch_prediction_job.error}")

    return batch_prediction_job

input_uri = "gs://doit-llm/batch/input/batch-multimodal.jsonl"
output_uri = "gs://doit-llm/batch/output/"
    
batch_generation(input_uri, output_uri)
