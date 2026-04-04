import json
import os

def create_audit_report_notebook():
    notebook = {
        "cells": [],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.9.0"}
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }

    def add_md(text):
        notebook["cells"].append({
            "cell_type": "markdown",
            "metadata": {},
            "source": [line + "\n" for line in text.split("\n")]
        })

    def add_code(text):
        notebook["cells"].append({
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [line + "\n" for line in text.split("\n")]
        })

    # 1. Executive Overview
    add_md("""# 1. Executive System Audit Overview
Comprehensive audit of survey paradata anomaly detection system.

Includes:
- Data validation
- Feature recomputation
- Rule engine verification
- Adversarial robustness testing
- Classification consistency
- Advanced correlation and fatigue analysis""")

    # 2. Environment Setup
    add_md("""# 2. Environment Setup
Import dependencies and resolve the project root directory.""")

    add_code("""import os, sys, glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style='whitegrid')

def resolve_root():
    current = os.getcwd()
    if os.path.exists(os.path.join(current, 'src')):
        return current
    elif os.path.exists(os.path.join(os.path.dirname(current), 'src')):
        return os.path.dirname(current)
    return current

PROJECT_ROOT = resolve_root()
os.chdir(PROJECT_ROOT)
print("Project Root:", PROJECT_ROOT)""")

    # 3. Data Ingestion
    add_md("""# 3. Data Ingestion
Load the latest combined feature dataset from the output directory.""")

    add_code("""def load_latest():
    output_dir = os.path.join(PROJECT_ROOT, 'output')
    
    # Priority 1: Combined full features
    fallback = os.path.join(output_dir, 'final_combined_features.csv')
    if os.path.exists(fallback):
        return fallback, pd.read_csv(fallback)
        
    # Priority 2: Latest individual export
    pattern = os.path.join(output_dir, 'features_output_*.csv')
    files = glob.glob(pattern)
    if files:
        latest = max(files, key=os.path.getctime)
        return latest, pd.read_csv(latest)
        
    # Priority 3: Academic fallback
    academic_fallback = os.path.join(output_dir, 'final_combined_features_400series.csv')
    if os.path.exists(academic_fallback):
        return academic_fallback, pd.read_csv(academic_fallback)
        
    raise FileNotFoundError("No feature files found in 'output/' directory.")

loaded_path, df = load_latest()
print("Data source:", os.path.abspath(loaded_path))
print("Shape:", df.shape)
print("Columns:", len(df.columns))""")

    # 4. Data Validation Layer
    add_md("""# 4. Data Validation Layer
Apply input validation checks: missing data, negative durations, invalid ratios, and logical inconsistencies between dependent metrics.""")

    add_code("""# Convert object columns to numeric where possible (pandas 3.x compatible)
for col in df.select_dtypes(include='object').columns:
    converted = pd.to_numeric(df[col], errors='coerce')
    if converted.notna().any():
        df[col] = converted

# Missing + invalid checks
df['flag_missing_data'] = df.isna().any(axis=1)

if 'V-01_total_interview_duration_ms' in df.columns:
    df['flag_negative_duration'] = df['V-01_total_interview_duration_ms'] < 0

if 'V-04_speed_trajectory_ratio' in df.columns:
    df['flag_invalid_ratio'] = df['V-04_speed_trajectory_ratio'].isna() | (df['V-04_speed_trajectory_ratio'] < 0)

# Logical inconsistencies
if all(c in df.columns for c in ['T-06_rt_mean', 'T-09_rt_min', 'T-10_rt_max']):
    df['flag_inconsistent_metrics'] = (
        (df['T-06_rt_mean'] < df['T-09_rt_min']) |
        (df['T-06_rt_mean'] > df['T-10_rt_max'])
    )

print("Validation flags created")""")

    # 5. Feature Recalculation
    add_md("""# 5. Feature Recalculation
Recompute only the aggregated metrics that can be verified from the flattened feature table itself.

Some raw-log metrics, such as back-navigation rate, cannot be recomputed exactly from the
final one-row-per-interview dataset because the event sequence is no longer present.""")

    add_code("""if all(c in df.columns for c in ['T-06_rt_mean', 'T-07_rt_median', 'T-09_rt_min', 'T-10_rt_max']):
    df['flag_stat_order_issue'] = (
        (df['T-09_rt_min'] > df['T-06_rt_mean']) |
        (df['T-06_rt_mean'] > df['T-10_rt_max']) |
        (df['T-09_rt_min'] > df['T-07_rt_median']) |
        (df['T-07_rt_median'] > df['T-10_rt_max'])
    )
else:
    df['flag_stat_order_issue'] = False""")

    # 6. Rule Engine Verification
    add_md("""# 6. Rule Engine Verification
Reapply the anomaly detection rules using the same thresholds as the pipeline anomaly detector:
- Too fast: total duration below 5000 ms
- Too slow: total duration above 3600000 ms
- IQR-based duration outlier detection (Q1 - 1.5*IQR, Q3 + 1.5*IQR)
- Low entropy (< 0.5), uniform timing (variance < 10)
- High back-navigation rate (> 0.5), zero back-navigation count""")

    add_code("""if 'V-01_total_interview_duration_ms' in df.columns:
    # Hard thresholds aligned with anomaly_detector.py
    df['flag_too_fast'] = df['V-01_total_interview_duration_ms'] < 5000
    df['flag_too_slow'] = df['V-01_total_interview_duration_ms'] > 3600000

    # IQR-based duration outlier (proposal Section 3.3, anomaly_detector.py Layer 3)
    if len(df) > 3:
        dur = df['V-01_total_interview_duration_ms']
        Q1, Q3 = dur.quantile(0.25), dur.quantile(0.75)
        IQR = Q3 - Q1
        df['flag_iqr_duration'] = (dur < Q1 - 1.5 * IQR) | (dur > Q3 + 1.5 * IQR)
    else:
        df['flag_iqr_duration'] = False

if 'T-03_rt_entropy' in df.columns:
    df['flag_low_entropy'] = df['T-03_rt_entropy'] < 0.5

if 'T-01_rt_variance' in df.columns:
    df['flag_uniform_timing'] = df['T-01_rt_variance'] < 10

if 'V-05_back_navigation_rate' in df.columns:
    df['flag_high_back_nav'] = df['V-05_back_navigation_rate'] > 0.5

if 'V-06_back_navigation_total_count' in df.columns:
    df['flag_zero_back_nav'] = df['V-06_back_navigation_total_count'] == 0""")

    # 7. Anomaly Scoring
    add_md("""# 7. Anomaly Scoring
Compute the weighted anomaly score using the same formula as the pipeline anomaly detector:
- flag_too_fast: weight 3
- flag_too_slow: weight 2
- flag_low_entropy: weight 2
- flag_uniform_timing: weight 2
- flag_high_back_nav: weight 1
- flag_invalid_ratio: weight 3""")

    add_code("""score = pd.Series(0, index=df.index)

score += df.get('flag_too_fast', pd.Series(False, index=df.index)).astype(int) * 3
score += df.get('flag_too_slow', pd.Series(False, index=df.index)).astype(int) * 2
score += df.get('flag_low_entropy', pd.Series(False, index=df.index)).astype(int) * 2
score += df.get('flag_uniform_timing', pd.Series(False, index=df.index)).astype(int) * 2
score += df.get('flag_high_back_nav', pd.Series(False, index=df.index)).astype(int) * 1
score += df.get('flag_invalid_ratio', pd.Series(False, index=df.index)).astype(int) * 3

df['computed_anomaly_score'] = score
if df['computed_anomaly_score'].max() > 0:
    df['normalized_score'] = df['computed_anomaly_score'] / df['computed_anomaly_score'].max()
else:
    df['normalized_score'] = 0.0""")

    # 8. Classification
    add_md("""# 8. Classification
Classify interviews into categories using the same logic as the current pipeline:
- Data quality issue (if flagged by DQ checks)
- Anomalous (score >= 5)
- Suspicious (score >= 2)
- Normal (score < 2)""")

    add_code("""def classify(row):
    if 'is_data_quality_issue' in df.columns and row.get('is_data_quality_issue', 0) == 1:
        return 'dq_issue'
    elif row['computed_anomaly_score'] >= 5:
        return 'anomalous'
    elif row['computed_anomaly_score'] >= 2:
        return 'suspicious'
    else:
        return 'normal'

df['computed_category'] = df.apply(classify, axis=1)""")

    # 9. Audit Consistency Checks
    add_md("""# 9. Audit Consistency Checks
Compare audit-recomputed scores and categories against the pipeline-produced values to verify deterministic reproducibility.""")

    add_code("""if 'anomaly_score' in df.columns:
    mismatch = (df['computed_anomaly_score'] != df['anomaly_score']).sum()
    print("Score mismatches:", mismatch)

if 'anomaly_category' in df.columns:
    mismatch_cat = (df['computed_category'] != df['anomaly_category']).sum()
    print("Category mismatches:", mismatch_cat)""")

    # 10. Summary Statistics
    add_md("""# 10. Summary Statistics
Descriptive statistics for all numeric features and flag distribution counts.""")

    add_code("""print(df.describe())

print("\\nFlag Distribution:")
flags = [col for col in df.columns if col.startswith('flag_')]
for f in flags:
    print(f, df[f].sum())""")

    # 11. Visualization
    add_md("""# 11. Visualization
Distribution of anomaly scores and category breakdown across the dataset.""")

    add_code("""plt.figure()
if df['computed_anomaly_score'].nunique() > 1:
    sns.histplot(df['computed_anomaly_score'], bins=20, kde=True)
else:
    sns.histplot(df['computed_anomaly_score'], bins=20, kde=False)
plt.title('Anomaly Score Distribution')
plt.show()

plt.figure()
sns.countplot(x='computed_category', data=df, order=['normal', 'suspicious', 'anomalous', 'dq_issue'])
plt.title('Category Distribution')
plt.show()""")

    # 12. Adversarial Edge Case Detection
    add_md("""# 12. Adversarial Edge Case Detection
Identify interviews with extreme or degenerate data: missing values, non-positive durations, zero entropy.""")

    add_code("""edge_condition = df['flag_missing_data'] == True

if 'V-01_total_interview_duration_ms' in df.columns:
    edge_condition = edge_condition | (df['V-01_total_interview_duration_ms'] <= 0)

if 'T-03_rt_entropy' in df.columns:
    edge_condition = edge_condition | (df['T-03_rt_entropy'] == 0)

edge_cases = df[edge_condition]
print("Edge Cases Detected:", len(edge_cases))
display(edge_cases.head() if not edge_cases.empty else "No edge cases matched.")""")

    # 13. Final Output
    add_md("""# 13. Final Output
Export the audit-enriched dataset with all recomputed flags, scores, and categories.""")

    add_code("""output_path = os.path.join(PROJECT_ROOT, 'output', 'audit_results.csv')
os.makedirs(os.path.dirname(output_path), exist_ok=True)
df.to_csv(output_path, index=False)
print("Audit results saved to:", output_path)""")

    # 14. Correlation Analysis
    add_md("""# 14. Correlation Analysis
Correlation heatmap of key structural and statistical paradata features to identify collinear metrics.""")

    add_code("""features_to_correlate = [
    'computed_anomaly_score', 'V-01_total_interview_duration_ms',
    'V-05_back_navigation_rate', 'T-01_rt_variance', 'T-03_rt_entropy',
    'T-06_rt_mean', 'S-05_pause_count_5s', 'S-10_section_completion_rate'
]
available_features = [f for f in features_to_correlate if f in df.columns]

if available_features:
    corr = df[available_features].corr()
    plt.figure(figsize=(10, 8))
    sns.heatmap(corr, annot=True, cmap='coolwarm', fmt=".2f", vmin=-1, vmax=1)
    plt.title('Feature Correlation Heatmap')
    plt.tight_layout()
    plt.show()
else:
    print("Required features for correlation analysis are missing from the dataframe.")""")

    # 15. Anomaly vs. Session Duration
    add_md("""# 15. Anomaly vs. Session Duration
Examining the relationship between total survey duration and the calculated anomaly score.""")

    add_code("""if 'V-01_total_interview_duration_ms' in df.columns and 'computed_anomaly_score' in df.columns:
    plt.figure(figsize=(10, 6))
    
    # Optional: filter out negative durations or highly extreme outliers for a cleaner plot
    plot_df = df[df['V-01_total_interview_duration_ms'] > 0]
    
    if not plot_df.empty:
        sns.scatterplot(
            data=plot_df, 
            x='V-01_total_interview_duration_ms', 
            y='computed_anomaly_score',
            hue='computed_category',
            palette={'normal':'#2ca02c', 'suspicious':'#ff7f0e', 'anomalous':'#d62728', 'dq_issue':'#9467bd'},
            alpha=0.7
        )
        plt.title('Anomaly Score vs Total Interview Duration')
        plt.xlabel('Total Interview Duration (ms)')
        plt.ylabel('Computed Anomaly Score')
        plt.xscale('log') # Log scale is often better for duration
        plt.tight_layout()
        plt.show()
    else:
        print("No valid duration data to plot.")""")

    # 16. Section-Level Fatigue Analysis
    add_md("""# 16. Section-Level Fatigue Analysis
Analyzing section-level features (pauses and section completion) by anomaly category to discover where anomalous respondents start showing fatigue.""")

    add_code("""s_features = ['S-05_pause_count_5s', 'S-07_mean_pause_duration_ms', 'S-10_section_completion_rate']
available_s = [f for f in s_features if f in df.columns]

if available_s and 'computed_category' in df.columns:
    fig, axes = plt.subplots(1, len(available_s), figsize=(6 * len(available_s), 5))
    if len(available_s) == 1:
        axes = [axes]
    
    for ax, feat in zip(axes, available_s):
        sns.boxplot(
            data=df, 
            x='computed_category', 
            y=feat, 
            ax=ax, 
            order=['normal', 'suspicious', 'anomalous', 'dq_issue'],
            palette={'normal':'#2ca02c', 'suspicious':'#ff7f0e', 'anomalous':'#d62728', 'dq_issue':'#9467bd'}
        )
        ax.set_title(f'{feat} by Category')
        ax.set_xticklabels(ax.get_xticklabels(), rotation=45)
    
    plt.tight_layout()
    plt.show()
else:
    print("S-Series parameters not available for Section-Level Fatigue Analysis.")""")

    # 17. Multidimensional Feature Pairplot
    add_md("""# 17. Multidimensional Feature Pairplot
Pairwise scatterplots to visually cluster behavioral subsets using timing and structural metrics.""")

    add_code("""pairplot_features = ['T-03_rt_entropy', 'T-06_rt_mean', 'V-05_back_navigation_rate', 'computed_category']
available_pair = [f for f in pairplot_features if f in df.columns]

if len(available_pair) > 1 and 'computed_category' in available_pair:
    sns.pairplot(
        df[available_pair], 
        hue='computed_category', 
        palette={'normal':'#2ca02c', 'suspicious':'#ff7f0e', 'anomalous':'#d62728', 'dq_issue':'#9467bd'}, 
        corner=True,
        diag_kind='hist',
        plot_kws={'alpha': 0.6}
    )
    plt.suptitle('Pairplot of Key Paradata Metrics', y=1.02)
    plt.show()
else:
    print("Required features for pairplot are missing.")""")

    # Write Notebook variants
    notebook_dir = os.path.join(os.getcwd(), 'notebooks')
    os.makedirs(notebook_dir, exist_ok=True)

    for filename in ['System_Audit_Report.ipynb', 'System_Audit_Report_Final.ipynb']:
        notebook_path = os.path.join(notebook_dir, filename)
        try:
            with open(notebook_path, 'w', encoding='utf-8') as f:
                json.dump(notebook, f, indent=2)
            print("Notebook created successfully at:", notebook_path)
        except Exception as e:
            print("ERROR saving notebook:", e)

if __name__ == '__main__':
    create_audit_report_notebook()
