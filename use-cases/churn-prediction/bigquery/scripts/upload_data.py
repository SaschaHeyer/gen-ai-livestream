import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
import os

# Path to your service account key file
# key_path = "path/to/your/service-account-key.json"
# credentials = service_account.Credentials.from_service_account_file(key_path)

# Or use application default credentials (recommended)
# Make sure you've run: gcloud auth application-default login

def upload_to_bigquery():
    """Upload the churn dataset to BigQuery."""
    # Load the CSV file into a pandas DataFrame
    data_path = "../data/churn.csv"
    churn_data = pd.read_csv(data_path)
    
    # Initialize BigQuery client
    client = bigquery.Client()
    
    # Define dataset and table
    dataset_id = "churn_prediction"
    table_id = "customer_data"
    
    # Create dataset if it doesn't exist
    dataset_ref = client.dataset(dataset_id)
    try:
        client.get_dataset(dataset_ref)
        print(f"Dataset {dataset_id} already exists")
    except Exception:
        # Dataset does not exist, so create it
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "US"  # Specify the location
        dataset = client.create_dataset(dataset)
        print(f"Dataset {dataset_id} created")

    # Define table reference
    table_ref = dataset_ref.table(table_id)
    
    # Create load job config
    job_config = bigquery.LoadJobConfig()
    job_config.write_disposition = bigquery.WriteDisposition.WRITE_TRUNCATE
    job_config.autodetect = True
    
    # Upload the data
    job = client.load_table_from_dataframe(
        churn_data, 
        table_ref,
        job_config=job_config
    )
    
    # Wait for the job to complete
    job.result()
    
    # Verify the data was loaded
    table = client.get_table(table_ref)
    print(f"Loaded {table.num_rows} rows to {dataset_id}.{table_id}")

if __name__ == "__main__":
    upload_to_bigquery()