import os
import sys
import argparse
from upload_data import upload_to_bigquery
from preprocess_data import preprocess_data
from train_model import train_churn_model
from make_predictions import make_predictions
from visualize_results import visualize_results

def main():
    """
    Run the entire churn prediction pipeline using BigQuery ML.
    """
    parser = argparse.ArgumentParser(description='Churn Prediction with BigQuery ML')
    parser.add_argument('--upload', action='store_true', help='Upload data to BigQuery')
    parser.add_argument('--preprocess', action='store_true', help='Preprocess data')
    parser.add_argument('--train', action='store_true', help='Train the model')
    parser.add_argument('--predict', action='store_true', help='Make predictions')
    parser.add_argument('--visualize', action='store_true', help='Visualize results')
    parser.add_argument('--all', action='store_true', help='Run all steps')
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    
    # Check if we should run all steps
    if args.all:
        args.upload = args.preprocess = args.train = args.predict = args.visualize = True
    
    # Run each step based on arguments
    if args.upload:
        print("Step 1: Uploading data to BigQuery...")
        upload_to_bigquery()
        print("Upload completed.\n")
    
    if args.preprocess:
        print("Step 2: Preprocessing data...")
        preprocess_data()
        print("Preprocessing completed.\n")
    
    if args.train:
        print("Step 3: Training the model...")
        train_churn_model()
        print("Training completed.\n")
    
    if args.predict:
        print("Step 4: Making predictions...")
        make_predictions()
        print("Predictions completed.\n")
    
    if args.visualize:
        print("Step 5: Creating visualizations...")
        visualize_results()
        print("Visualizations completed.\n")
    
    print("All specified steps have been completed.")

if __name__ == "__main__":
    main()