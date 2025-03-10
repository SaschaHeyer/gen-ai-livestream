import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from make_predictions import make_predictions

def visualize_results(viz_data=None):
    """
    Create visualizations from prediction results
    """
    if viz_data is None:
        print("Fetching prediction data...")
        viz_data = make_predictions()
    
    # Set style for plots
    sns.set(style="whitegrid")
    
    # Create a figure with multiple subplots
    fig = plt.figure(figsize=(15, 12))
    
    # 1. Churn probability distribution
    plt.subplot(2, 2, 1)
    sns.histplot(data=viz_data, x='churn_probability', hue='Exited', bins=20, kde=True)
    plt.title('Churn Probability Distribution')
    plt.xlabel('Churn Probability')
    plt.ylabel('Count')
    
    # 2. Age vs Churn Probability
    plt.subplot(2, 2, 2)
    sns.scatterplot(data=viz_data, x='Age', y='churn_probability', hue='Exited', alpha=0.6)
    plt.title('Age vs Churn Probability')
    plt.xlabel('Age')
    plt.ylabel('Churn Probability')
    
    # 3. Balance vs Churn Probability
    plt.subplot(2, 2, 3)
    sns.scatterplot(data=viz_data, x='Balance', y='churn_probability', hue='Exited', alpha=0.6)
    plt.title('Balance vs Churn Probability')
    plt.xlabel('Balance')
    plt.ylabel('Churn Probability')
    
    # 4. IsActiveMember vs Churn Probability
    plt.subplot(2, 2, 4)
    sns.boxplot(data=viz_data, x='IsActiveMember', y='churn_probability', hue='Exited')
    plt.title('Active Member Status vs Churn Probability')
    plt.xlabel('Is Active Member')
    plt.ylabel('Churn Probability')
    
    # Adjust layout and save figure
    plt.tight_layout()
    plt.savefig('../bigquery/churn_visualization.png')
    plt.show()
    
    # Create confusion matrix visualization
    # We need to create this from our visualization data
    confusion_df = pd.DataFrame({
        'Actual': viz_data['Exited'],
        'Predicted': viz_data['predicted_Exited']
    })
    
    confusion_matrix = pd.crosstab(confusion_df['Actual'], confusion_df['Predicted'], 
                                   rownames=['Actual'], colnames=['Predicted'])
    
    plt.figure(figsize=(8, 6))
    sns.heatmap(confusion_matrix, annot=True, fmt='d', cmap='Blues', cbar=False)
    plt.title('Confusion Matrix (Sample)')
    plt.tight_layout()
    plt.savefig('../bigquery/confusion_matrix.png')
    plt.show()
    
    # Calculate and display metrics based on our visualization sample
    TP = sum((confusion_df['Actual'] == 1) & (confusion_df['Predicted'] == 1))
    FP = sum((confusion_df['Actual'] == 0) & (confusion_df['Predicted'] == 1))
    FN = sum((confusion_df['Actual'] == 1) & (confusion_df['Predicted'] == 0))
    TN = sum((confusion_df['Actual'] == 0) & (confusion_df['Predicted'] == 0))
    
    accuracy = (TP + TN) / len(confusion_df)
    precision = TP / (TP + FP) if (TP + FP) > 0 else 0
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    print(f"Sample Metrics (based on {len(confusion_df)} samples):")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")
    print(f"F1 Score: {f1:.4f}")
    
if __name__ == "__main__":
    visualize_results()