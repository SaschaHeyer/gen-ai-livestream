# Churn Prediction with BigQuery ML

This project demonstrates how to implement a customer churn prediction model using Google BigQuery ML. The implementation mirrors the approach found in the `../notebook/basic.ipynb` file, but leverages BigQuery for scalable data processing and model training.

## Overview

The project includes a complete ML pipeline for churn prediction:

1. **Data Upload**: Uploading the CSV data to BigQuery
2. **Data Preprocessing**: Cleaning and feature engineering in BigQuery using SQL
3. **Model Training**: Training a Random Forest classifier using BigQuery ML
4. **Model Evaluation**: Evaluating the model's performance with metrics and feature importance
5. **Prediction**: Making predictions on customer data
6. **Visualization**: Visualizing the results and model performance

## Prerequisites

- Google Cloud Platform account with BigQuery enabled
- `gcloud` CLI installed and configured
- Python 3.7+
- Required Python packages (see `requirements.txt`)

## Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd use-cases/churn-prediction/bigquery
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Authenticate with Google Cloud:
   ```bash
   gcloud auth application-default login
   ```

## Usage

You can run the entire pipeline or individual steps using the `main.py` script:

```bash
# Run the entire pipeline
python scripts/main.py --all

# Or run individual steps
python scripts/main.py --upload      # Upload data to BigQuery
python scripts/main.py --preprocess  # Preprocess the data
python scripts/main.py --train       # Train the model
python scripts/main.py --predict     # Generate predictions
python scripts/main.py --visualize   # Create visualizations
```

## Project Structure

```
bigquery/
├── README.md
├── requirements.txt
└── scripts/
    ├── main.py               # Main script to run the pipeline
    ├── upload_data.py        # Script to upload data to BigQuery
    ├── preprocess_data.py    # Script for data preprocessing
    ├── train_model.py        # Script for model training
    ├── make_predictions.py   # Script for making predictions
    └── visualize_results.py  # Script for visualizing results
```

## Implementation Details

### Data Preprocessing

- Label encoding for categorical variables
- One-hot encoding for geography
- Feature selection based on importance

### Model Training

- Random Forest Classifier with hyperparameter tuning
- Cross-validation for model evaluation
- Feature importance analysis

## Results

After running the pipeline, visualizations will be saved to the `bigquery/` directory:
- `churn_visualization.png`: Visualization of churn probabilities
- `confusion_matrix.png`: Confusion matrix of model predictions

## Further Improvements

- Implement more model types (XGBoost, Neural Networks)
- Add more feature engineering techniques
- Create a dashboard for real-time monitoring
- Implement model deployment and serving
