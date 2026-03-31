import pandas as pd
import numpy as np
import os
import glob

def generate_visualizations():
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib is not installed. Run `pip install matplotlib` to generate graphical plots.")
        print("Skipping visualization image rendering.")
        return

    os.makedirs('output/plots', exist_ok=True)
    
    # Locate dataset — check timestamped outputs first, then fallbacks
    files = glob.glob('output/features_output_*.csv')
    if files:
        file_path = max(files, key=os.path.getctime)
    elif os.path.exists('output/final_combined_features.csv'):
        file_path = 'output/final_combined_features.csv'
    elif os.path.exists('output/final_combined_features_400series.csv'):
        file_path = 'output/final_combined_features_400series.csv'
    else:
        print(
            "[WARN] No pipeline output file found in output/. "
            "Run `python run_pipeline.py` first to generate features."
        )
        return

    print(f"Reading dataset from {file_path}")
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"[ERROR] Could not read {file_path}: {e}")
        return
    
    if df.empty:
        print("Dataset is empty.")
        return
        
    # Plot 1: Anomaly Score Distribution
    plt.figure(figsize=(10, 6))
    scores = df['anomaly_score'].dropna()
    plt.hist(scores, bins=15, color='skyblue', edgecolor='black', alpha=0.7)
    plt.title('Distribution of Anomaly Scores Across Global Paradata Logs', fontsize=14)
    plt.xlabel('Calculated Anomaly Score (15-Point Normalized)', fontsize=12)
    plt.ylabel('Frequency (Interviews)', fontsize=12)
    plt.axvline(x=5, color='green', linestyle='--', label='Suspicious Threshold (>5)')
    plt.axvline(x=9, color='red', linestyle='--', label='Anomalous Threshold (>9)')
    plt.legend()
    plt.tight_layout()
    plt.savefig('output/plots/anomaly_distribution.png', dpi=300)
    plt.close()
    
    # Plot 2: Total Duration vs Response Time Variance (Scatter)
    if 'V-01_total_interview_duration_ms' in df.columns and 'T-01_rt_variance' in df.columns:
        plt.figure(figsize=(10, 6))
        # Filter extreme outliers for visualization clarity
        q95 = df['V-01_total_interview_duration_ms'].quantile(0.95)
        clean_df = df[df['V-01_total_interview_duration_ms'] <= q95]
        
        # Color code by anomaly status
        colors = clean_df['anomaly_category'].map({'normal': 'blue', 'suspicious': 'yellow', 'strong_anomaly': 'red', 'dq_issue': 'black', 'anomalous': 'red'})
        
        plt.scatter(clean_df['V-01_total_interview_duration_ms'] / 1000, 
                    clean_df['T-01_rt_variance'] / 1000, 
                    c=colors.fillna('grey'), alpha=0.6, edgecolors='w', s=80)
        plt.title('Feature Correlation: Duration vs RT Variance', fontsize=14)
        plt.xlabel('Total Complete Interview Duration (Seconds)', fontsize=12)
        plt.ylabel('RT Variance (Thousands)', fontsize=12)
        plt.tight_layout()
        plt.savefig('output/plots/duration_vs_variance_scatter.png', dpi=300)
        plt.close()

    # Plot 3: Categorical Breakdown (Pie Chart)
    if 'anomaly_category' in df.columns:
        plt.figure(figsize=(8, 8))
        counts = df['anomaly_category'].value_counts()
        plt.pie(counts, labels=counts.index, autopct='%1.1f%%', startangle=140, colors=['#4CAF50', '#FFC107', '#F44336', '#9E9E9E'])
        plt.title('Proportional Distribution of Classification Outcomes', fontsize=14)
        plt.tight_layout()
        plt.savefig('output/plots/categorical_pie_chart.png', dpi=300)
        plt.close()

    print(" Generated 3 academic visualizations in output/plots/")

if __name__ == "__main__":
    generate_visualizations()
