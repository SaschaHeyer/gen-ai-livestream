from google.cloud import aiplatform
from typing import List, Dict

def predict_tabular_classification_sample(
    project: str,
    location: str,
    endpoint_name: str,
    instances: List[Dict],
):
    """
    Submits instances to a Vertex AI endpoint for online prediction.

    Args:
        project: Your Google Cloud project ID.
        location: Region where the Endpoint is located (e.g., "us-central1").
        endpoint_name: A fully qualified endpoint name or endpoint ID.
                       Example: "projects/123/locations/us-central1/endpoints/456"
                       or "456" if the project and location are already initialized.
        instances: A list of dictionaries, each representing one data row.
    """
    # Initialize the Vertex AI SDK with your project and region.
    aiplatform.init(project=project, location=location)

    # Initialize the endpoint.
    endpoint = aiplatform.Endpoint(endpoint_name)

    # Make the prediction.
    response = endpoint.predict(instances=instances)

    # Print out the prediction results.
    print("Prediction results:")
    for prediction in response.predictions:
        print(prediction)

if __name__ == "__main__":
    # Replace with your project ID, region, and endpoint ID or full resource name.
    project = "sascha-playground-doit"
    location = "us-central1"
    endpoint_name = "projects/sascha-playground-doit/locations/us-central1/endpoints/7477599360109248512"

    # Dummy input data that mimics a row from your dataset.
    # Note: Ensure that the data types and field names match what your model expects.
    instances = [
        {
            "RowNumber": "1",
            "CustomerId": "15634602",
            "Surname": "Hargrave",
            "CreditScore": "619",
            "Geography": "France",
            "Gender": "Female",
            "Age": "42",
            "Tenure": "2",
            "Balance": 0.0,           # Using a float for Balance as defined in your schema.
            "NumOfProducts": "1",
            "HasCrCard": "1",
            "IsActiveMember": "1",
            "EstimatedSalary": 101348.88,  # A float as defined.
            "Exited": "1"             # Even if Exited is the target, include it if your model requires it.
        }
    ]

    # Call the prediction function.
    predict_tabular_classification_sample(project, location, endpoint_name, instances)
