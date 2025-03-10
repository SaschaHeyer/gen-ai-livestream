from google.cloud import bigquery

def preprocess_data():
    """
    Perform data preprocessing and feature engineering in BigQuery
    including one-hot encoding for categorical variables.
    """
    client = bigquery.Client()
    
    # Define dataset and table references
    dataset_id = "churn_prediction"
    source_table_id = "customer_data"
    preprocessed_table_id = "preprocessed_data"
    
    # Check if the dataset exists
    dataset_ref = client.dataset(dataset_id)
    try:
        client.get_dataset(dataset_ref)
    except Exception as e:
        print(f"Dataset {dataset_id} does not exist: {e}")
        return
    
    # Preprocessing SQL query
    # This query:
    # 1. Converts Gender to binary (1 for Male, 0 for Female)
    # 2. Creates one-hot encoded columns for Geography
    # 3. Selects relevant features
    
    preprocessing_query = f"""
    CREATE OR REPLACE TABLE `{dataset_id}.{preprocessed_table_id}` AS
    SELECT
      CreditScore,
      CASE WHEN Gender = 'Male' THEN 1 ELSE 0 END AS Gender,
      Age,
      Tenure,
      Balance,
      NumOfProducts,
      HasCrCard,
      IsActiveMember,
      EstimatedSalary,
      CASE WHEN Geography = 'France' THEN 1 ELSE 0 END AS Geography_France,
      CASE WHEN Geography = 'Germany' THEN 1 ELSE 0 END AS Geography_Germany,
      CASE WHEN Geography = 'Spain' THEN 1 ELSE 0 END AS Geography_Spain,
      Exited
    FROM
      `{dataset_id}.{source_table_id}`;
    """
    
    # Execute the preprocessing query
    query_job = client.query(preprocessing_query)
    query_job.result()  # Wait for the query to complete
    
    # Get the preprocessed table and print info
    preprocessed_table = client.get_table(f"{dataset_id}.{preprocessed_table_id}")
    print(f"Created preprocessed table with {preprocessed_table.num_rows} rows and {len(preprocessed_table.schema)} columns")
    
    # Print schema of the preprocessed table
    print("\nTable Schema:")
    for field in preprocessed_table.schema:
        print(f"{field.name}: {field.field_type}")
    
if __name__ == "__main__":
    preprocess_data()