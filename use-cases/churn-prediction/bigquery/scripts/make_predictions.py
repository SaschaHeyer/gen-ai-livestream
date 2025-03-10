from google.cloud import bigquery
import pandas as pd

def make_predictions():
    """
    Use the trained model to make predictions on the data
    and calculate confusion matrix and other metrics.
    """
    client = bigquery.Client()
    
    # Define dataset references
    dataset_id = "churn_prediction"
    model_id = "churn_model"
    preprocessed_table_id = "preprocessed_data"
    prediction_table_id = "predictions"
    
    # SQL query to make predictions
    prediction_query = f"""
    CREATE OR REPLACE TABLE `{dataset_id}.{prediction_table_id}` AS
    SELECT
      *,
      ML.PREDICT(MODEL `{dataset_id}.{model_id}`, t) as predicted
    FROM
      `{dataset_id}.{preprocessed_table_id}` as t
    """
    
    # Execute the prediction query
    prediction_job = client.query(prediction_query)
    prediction_job.result()  # Wait for the query to complete
    
    # Get confusion matrix
    confusion_matrix_query = f"""
    SELECT
      COUNT(CASE WHEN Exited = 1 AND predicted.predicted_Exited = 1 THEN 1 END) AS true_positive,
      COUNT(CASE WHEN Exited = 0 AND predicted.predicted_Exited = 1 THEN 1 END) AS false_positive,
      COUNT(CASE WHEN Exited = 1 AND predicted.predicted_Exited = 0 THEN 1 END) AS false_negative,
      COUNT(CASE WHEN Exited = 0 AND predicted.predicted_Exited = 0 THEN 1 END) AS true_negative
    FROM
      `{dataset_id}.{prediction_table_id}`
    """
    
    confusion_job = client.query(confusion_matrix_query)
    confusion_results = confusion_job.result()
    
    # Print confusion matrix
    for row in confusion_results:
        tp = row.true_positive
        fp = row.false_positive
        fn = row.false_negative
        tn = row.true_negative
        
        print("\nConfusion Matrix:")
        print(f"True Positive: {tp}")
        print(f"False Positive: {fp}")
        print(f"False Negative: {fn}")
        print(f"True Negative: {tn}")
        
        # Calculate metrics
        accuracy = (tp + tn) / (tp + tn + fp + fn)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        print("\nMetrics:")
        print(f"Accuracy: {accuracy:.4f}")
        print(f"Precision: {precision:.4f}")
        print(f"Recall: {recall:.4f}")
        print(f"F1 Score: {f1:.4f}")
    
    # Get some example predictions
    example_query = f"""
    SELECT
      CreditScore,
      Age,
      Tenure,
      Balance,
      NumOfProducts,
      HasCrCard,
      IsActiveMember,
      EstimatedSalary,
      Geography_Spain,
      Geography_Germany,
      Exited AS actual_churn,
      predicted.predicted_Exited AS predicted_churn,
      predicted.probability[OFFSET(1)].probability AS churn_probability
    FROM
      `{dataset_id}.{prediction_table_id}`
    LIMIT 10
    """
    
    example_job = client.query(example_query)
    example_results = example_job.result()
    
    # Convert to pandas DataFrame for easier viewing
    examples_df = example_job.to_dataframe()
    
    print("\nExample Predictions:")
    print(examples_df)
    
    # Create a visualization query for data analysis
    visualization_query = f"""
    SELECT
      Age,
      Balance,
      IsActiveMember,
      Exited,
      predicted.predicted_Exited,
      predicted.probability[OFFSET(1)].probability AS churn_probability
    FROM
      `{dataset_id}.{prediction_table_id}`
    ORDER BY churn_probability DESC
    LIMIT 1000
    """
    
    viz_job = client.query(visualization_query)
    viz_data = viz_job.to_dataframe()
    
    # This data can be used for visualization or further analysis
    print(f"\nVisualization data shape: {viz_data.shape}")
    
    return viz_data
    
if __name__ == "__main__":
    make_predictions()