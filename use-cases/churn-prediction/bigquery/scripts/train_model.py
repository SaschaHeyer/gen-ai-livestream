from google.cloud import bigquery

def train_churn_model():
    """
    Train a Random Forest model for churn prediction using BigQuery ML.
    """
    client = bigquery.Client()
    
    # Define dataset references
    dataset_id = "churn_prediction"
    preprocessed_table_id = "preprocessed_data"
    model_id = "churn_model"
    
    # Feature selection
    features = [
        "CreditScore", 
        "Age", 
        "Tenure", 
        "Balance", 
        "NumOfProducts", 
        "HasCrCard", 
        "IsActiveMember", 
        "EstimatedSalary", 
        "Geography_Spain",
        "Geography_Germany"
    ]
    
    # Create a comma-separated string of features
    features_str = ", ".join(features)
    
    # SQL query to train a Random Forest model
    training_query = f"""
    CREATE OR REPLACE MODEL `{dataset_id}.{model_id}`
    OPTIONS(
      model_type='RANDOM_FOREST_CLASSIFIER',
      input_label_cols=['Exited'],
      data_split_method='AUTO_SPLIT',
      num_trials=20,
      max_tree_depth=10
    ) AS
    SELECT
      {features_str},
      Exited
    FROM
      `{dataset_id}.{preprocessed_table_id}`
    """
    
    # Execute the training query
    print("Starting model training...")
    query_job = client.query(training_query)
    query_job.result()  # Wait for the query to complete
    
    print(f"Model `{dataset_id}.{model_id}` has been created successfully.")
    
    # Get model evaluation metrics
    eval_query = f"""
    SELECT
      *
    FROM
      ML.EVALUATE(MODEL `{dataset_id}.{model_id}`)
    """
    
    eval_job = client.query(eval_query)
    eval_results = eval_job.result()
    
    print("\nModel Evaluation Metrics:")
    for row in eval_results:
        print(f"Precision: {row.precision}")
        print(f"Recall: {row.recall}")
        print(f"Accuracy: {row.accuracy}")
        print(f"F1 Score: {row.f1_score}")
        print(f"Log Loss: {row.log_loss}")
        print(f"ROC AUC: {row.roc_auc}")
    
    # Feature importance
    feature_importance_query = f"""
    SELECT
      *
    FROM
      ML.FEATURE_IMPORTANCE(MODEL `{dataset_id}.{model_id}`)
    ORDER BY importance DESC
    """
    
    feature_job = client.query(feature_importance_query)
    feature_results = feature_job.result()
    
    print("\nFeature Importance:")
    for row in feature_results:
        print(f"{row.feature}: {row.importance:.4f}")
    
if __name__ == "__main__":
    train_churn_model()