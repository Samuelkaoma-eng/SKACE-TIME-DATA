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
Import dependencies, resolve the project root directory, and load the live
detector/reporting helpers used by the production pipeline.""")

    add_code("""import os, sys, glob, subprocess, warnings
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from IPython.display import display

sns.set_theme(style='whitegrid')
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=FutureWarning, module='seaborn')

def resolve_root():
    current = os.getcwd()
    if os.path.exists(os.path.join(current, 'src')):
        return current
    elif os.path.exists(os.path.join(os.path.dirname(current), 'src')):
        return os.path.dirname(current)
    return current

PROJECT_ROOT = resolve_root()
os.chdir(PROJECT_ROOT)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.validation.anomaly_detector import AnomalyDetector
from src.validation.reporting import feature_dataset_view

print("Project Root:", PROJECT_ROOT)""")

    # 3. Data Ingestion
    add_md("""# 3. Data Ingestion
Load a selected combined feature dataset from the output directory, then attach
the matching question-level and section-level tables when available.""")

    add_code("""PREFERRED_RUN_LABEL = os.environ.get('SKACE_NOTEBOOK_RUN_LABEL', 'canonical_validation')
ALLOW_FALLBACK_TO_LATEST = False

print("Preferred run label:", PREFERRED_RUN_LABEL)
print("Fallback to latest if preferred run is missing:", ALLOW_FALLBACK_TO_LATEST)""")

    add_code("""def list_pipeline_outputs():
    output_dir = os.path.join(PROJECT_ROOT, 'output')
    pattern = os.path.join(output_dir, 'pipeline_output_*.csv')
    files = glob.glob(pattern)
    return sorted(files, key=os.path.getctime, reverse=True)

def find_dataset_for_label(run_label):
    if not run_label:
        return None, None
    candidate = os.path.join(PROJECT_ROOT, 'output', f'pipeline_output_{run_label}.csv')
    if os.path.exists(candidate):
        return candidate, pd.read_csv(candidate)
    return None, None

def find_dataset_with_fallback(preferred_run_label):
    output_dir = os.path.join(PROJECT_ROOT, 'output')
    selected_path, selected_df = find_dataset_for_label(preferred_run_label)
    if selected_path is not None:
        return selected_path, selected_df

    canonical_path, canonical_df = find_dataset_for_label('canonical_validation')
    if canonical_path is not None:
        return canonical_path, canonical_df

    bootstrap_path, bootstrap_df = find_dataset_for_label('notebook_bootstrap')
    if bootstrap_path is not None:
        return bootstrap_path, bootstrap_df

    if ALLOW_FALLBACK_TO_LATEST:
        available = list_pipeline_outputs()
        if available:
            latest = available[0]
            return latest, pd.read_csv(latest)

    # Historical compatibility fallbacks
    fallback = os.path.join(output_dir, 'final_combined_features.csv')
    if os.path.exists(fallback):
        return fallback, pd.read_csv(fallback)
        
    # Priority 3: Latest individual feature export
    pattern = os.path.join(output_dir, 'features_output_*.csv')
    files = glob.glob(pattern)
    if files:
        latest = max(files, key=os.path.getctime)
        return latest, pd.read_csv(latest)
        
    # Priority 4: Academic fallback
    academic_fallback = os.path.join(output_dir, 'final_combined_features_400series.csv')
    if os.path.exists(academic_fallback):
        return academic_fallback, pd.read_csv(academic_fallback)

    return None, None

def bootstrap_pipeline_output():
    canonical_inputs = [
        os.path.join(PROJECT_ROOT, 'data', 'odk.csv'),
        os.path.join(PROJECT_ROOT, 'data', 'surveycto.csv'),
    ]
    if not all(os.path.exists(path) for path in canonical_inputs):
        raise FileNotFoundError(
            "No feature files found in 'output/' and canonical data inputs are missing. "
            "Run `python run_pipeline.py --inputs ...` first."
        )

    cmd = [
        sys.executable,
        'run_pipeline.py',
        '--parser', 'auto',
        '--output-dir', 'output',
        '--label', 'notebook_bootstrap',
        '--inputs',
        *canonical_inputs,
    ]
    ground_truth = os.path.join(PROJECT_ROOT, 'data', 'ground_truth_labels.csv')
    if os.path.exists(ground_truth):
        cmd.extend(['--ground-truth', ground_truth])

    print("No pipeline output found. Bootstrapping canonical pipeline run...")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        raise RuntimeError(
            "Automatic notebook bootstrap failed. "
            "Run `python run_pipeline.py --inputs data/odk.csv data/surveycto.csv` manually."
        )

def load_selected_dataset():
    loaded_path, df = find_dataset_with_fallback(PREFERRED_RUN_LABEL)
    if loaded_path is None:
        available_outputs = list_pipeline_outputs()
        if available_outputs and not ALLOW_FALLBACK_TO_LATEST:
            raise FileNotFoundError(
                "Preferred run label was not found and fallback-to-latest is disabled. "
                "Set SKACE_NOTEBOOK_RUN_LABEL to one of the available pipeline_output labels "
                "or set ALLOW_FALLBACK_TO_LATEST = True."
            )
        bootstrap_pipeline_output()
        loaded_path, df = find_dataset_with_fallback(PREFERRED_RUN_LABEL)

    if loaded_path is None:
        raise FileNotFoundError("No feature files found in 'output/' directory after notebook bootstrap.")

    return loaded_path, df

def derive_run_label(path):
    basename = os.path.splitext(os.path.basename(path))[0]
    for prefix in ['pipeline_output_', 'feature_dataset_', 'features_output_']:
        if basename.startswith(prefix):
            return basename[len(prefix):]
    return None

def resolve_input_paths_from_loaded_df(source_df):
    if 'file_name' not in source_df.columns:
        return []

    resolved = []
    for file_name in source_df['file_name'].dropna().astype(str).unique():
        matches = glob.glob(os.path.join(PROJECT_ROOT, 'data', '**', file_name), recursive=True)
        if not matches:
            return []
        resolved.append(matches[0])
    return resolved

def load_granular_outputs(source_path):
    run_label = derive_run_label(source_path)
    question_path = None
    section_path = None
    question_df = pd.DataFrame()
    section_df = pd.DataFrame()

    if run_label:
        question_candidate = os.path.join(PROJECT_ROOT, 'output', f'question_features_{run_label}.csv')
        section_candidate = os.path.join(PROJECT_ROOT, 'output', f'section_features_{run_label}.csv')

        if os.path.exists(question_candidate):
            question_path = question_candidate
            question_df = pd.read_csv(question_candidate)

        if os.path.exists(section_candidate):
            section_path = section_candidate
            section_df = pd.read_csv(section_candidate)

    return question_path, question_df, section_path, section_df

def ensure_granular_outputs(source_path, source_df):
    question_path, question_df, section_path, section_df = load_granular_outputs(source_path)
    if not question_df.empty and not section_df.empty:
        return question_path, question_df, section_path, section_df

    run_label = derive_run_label(source_path)
    input_paths = resolve_input_paths_from_loaded_df(source_df)
    if not run_label or not input_paths:
        return question_path, question_df, section_path, section_df

    cmd = [
        sys.executable,
        'run_pipeline.py',
        '--parser', 'auto',
        '--output-dir', 'output',
        '--label', run_label,
        '--inputs',
        *input_paths,
    ]
    ground_truth = os.path.join(PROJECT_ROOT, 'data', 'ground_truth_labels.csv')
    if os.path.exists(ground_truth) and run_label in ['canonical_validation', 'notebook_bootstrap']:
        cmd.extend(['--ground-truth', ground_truth])

    print("Granular outputs missing for selected run. Rebuilding them from raw inputs...")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print("Granular output rebuild failed; continuing without them.")
        return question_path, question_df, section_path, section_df

    return load_granular_outputs(source_path)

available_outputs = list_pipeline_outputs()
print("Available pipeline outputs (newest first):")
for path in available_outputs[:10]:
    print(" -", os.path.basename(path))

loaded_path, df = load_selected_dataset()
question_path, question_df, section_path, section_df = ensure_granular_outputs(loaded_path, df)
CURRENT_RUN_LABEL = derive_run_label(loaded_path) or 'manual'
print("Data source:", os.path.abspath(loaded_path))
print("Shape:", df.shape)
print("Columns:", len(df.columns))
print("Resolved run label:", CURRENT_RUN_LABEL)
print("Question feature file:", question_path if question_path else "not found for this run")
print("Section feature file:", section_path if section_path else "not found for this run")""")

    add_md("""# 3.1 Granular Feature Tables
Preview the question-level and section-level outputs emitted by the pipeline for
the same run label. These tables preserve the detailed feature grain before the
interview-level feature dataset is flattened for anomaly detection.""")

    add_code("""if question_df.empty:
    print("Question-level output not available for the loaded run.")
else:
    print("Question-level shape:", question_df.shape)
    display(question_df.head())

if section_df.empty:
    print("Section-level output not available for the loaded run.")
else:
    print("Section-level shape:", section_df.shape)
    display(section_df.head())""")

    # 4. Data Validation Layer
    add_md("""# 4. Data Validation Layer
Apply general audit diagnostics: missing data, negative durations, invalid ratios,
and logical inconsistencies between dependent metrics. These `audit_*` checks are
for exploratory auditing and are separate from the production detector.""")

    add_code("""# Convert object columns to numeric where possible (pandas 3.x compatible)
for col in df.select_dtypes(include='object').columns:
    converted = pd.to_numeric(df[col], errors='coerce')
    if converted.notna().any():
        df.loc[:, col] = converted

# Missing + invalid checks
df.loc[:, 'audit_missing_data'] = df.isna().any(axis=1)

if 'V-01_total_interview_duration_ms' in df.columns:
    df.loc[:, 'audit_negative_duration'] = df['V-01_total_interview_duration_ms'] < 0

if 'V-04_speed_trajectory_ratio' in df.columns:
    df.loc[:, 'audit_invalid_ratio'] = df['V-04_speed_trajectory_ratio'].isna() | (df['V-04_speed_trajectory_ratio'] < 0)

# Logical inconsistencies
if all(c in df.columns for c in ['T-06_rt_mean', 'T-09_rt_min', 'T-10_rt_max']):
    df.loc[:, 'audit_inconsistent_metrics'] = (
        (df['T-06_rt_mean'] < df['T-09_rt_min']) |
        (df['T-06_rt_mean'] > df['T-10_rt_max'])
    )

print("Audit diagnostics created")""")

    # 5. Feature Recalculation
    add_md("""# 5. Feature Recalculation
Recompute only the aggregated metrics that can be verified from the flattened feature table itself.

Some raw-log metrics, such as back-navigation rate, cannot be recomputed exactly from the
final one-row-per-interview dataset because the event sequence is no longer present.""")

    add_code("""if all(c in df.columns for c in ['T-06_rt_mean', 'T-07_rt_median', 'T-09_rt_min', 'T-10_rt_max']):
    df.loc[:, 'flag_stat_order_issue'] = (
        (df['T-09_rt_min'] > df['T-06_rt_mean']) |
        (df['T-06_rt_mean'] > df['T-10_rt_max']) |
        (df['T-09_rt_min'] > df['T-07_rt_median']) |
        (df['T-07_rt_median'] > df['T-10_rt_max'])
    )
else:
    df.loc[:, 'flag_stat_order_issue'] = False""")

    # 6. Live Detector Reproduction
    add_md("""# 6. Live Detector Reproduction
Recompute anomaly flags, scores, categories, and status using the production
`AnomalyDetector` directly. This avoids drift between the notebook and the live
pipeline logic.""")

    add_code("""detector_input = feature_dataset_view(df)
detector = AnomalyDetector()
recomputed = detector.detect(detector_input)

for col in [
    'anomaly_score', 'anomaly_category', 'status', 'flagged_features',
    'iqr_flags', 'rule_flags', 'is_data_quality_issue', 'is_anomalous_behavior', 'is_anomalous'
]:
    if col in recomputed.columns:
        df.loc[:, f'recomputed_{col}'] = recomputed[col]

df.loc[:, 'computed_anomaly_score'] = df.get('recomputed_anomaly_score', pd.Series(0, index=df.index))
df.loc[:, 'computed_category'] = df.get('recomputed_anomaly_category', pd.Series('unknown', index=df.index))

if pd.to_numeric(df['computed_anomaly_score'], errors='coerce').max() > 0:
    df.loc[:, 'normalized_score'] = pd.to_numeric(df['computed_anomaly_score'], errors='coerce') / pd.to_numeric(df['computed_anomaly_score'], errors='coerce').max()
else:
    df.loc[:, 'normalized_score'] = 0.0

print("Production detector reapplied to", len(recomputed), "rows")""")

    # 7. Audit Consistency Checks
    add_md("""# 7. Audit Consistency Checks
Compare the live detector recomputation against the source file when the loaded
dataset already contains pipeline-produced anomaly outputs.""")

    add_code("""comparison_pairs = [
    ('anomaly_score', 'recomputed_anomaly_score'),
    ('anomaly_category', 'recomputed_anomaly_category'),
    ('status', 'recomputed_status'),
    ('flagged_features', 'recomputed_flagged_features'),
]

comparison_summary = []
for source_col, recomputed_col in comparison_pairs:
    if source_col in df.columns and recomputed_col in df.columns:
        mismatches = (df[source_col].fillna('').astype(str) != df[recomputed_col].fillna('').astype(str)).sum()
        comparison_summary.append({
            'column': source_col,
            'mismatches': int(mismatches),
        })

if comparison_summary:
    comparison_df = pd.DataFrame(comparison_summary)
    display(comparison_df)
else:
    print("Loaded dataset does not contain source anomaly outputs to compare against.")""")

    # 8. Summary Statistics
    add_md("""# 8. Summary Statistics
Descriptive statistics for all numeric features and flag distribution counts.""")

    add_code("""print(df.describe())

print("\\nFlag Distribution:")
flags = [col for col in df.columns if col.startswith('flag_') or col.startswith('audit_')]
for f in flags:
    print(f, df[f].sum())""")

    # 9. Visualization
    add_md("""# 9. Visualization
Distribution of anomaly scores and category breakdown across the dataset.""")

    add_code("""plt.figure()
if df['computed_anomaly_score'].nunique() > 1:
    sns.histplot(df['computed_anomaly_score'], bins=20, kde=True)
else:
    sns.histplot(df['computed_anomaly_score'], bins=20, kde=False)
plt.title('Anomaly Score Distribution')
plt.show()

plt.figure()
sns.countplot(
    data=df,
    x='computed_category',
    hue='computed_category',
    order=['normal', 'suspicious', 'anomalous', 'dq_issue'],
    hue_order=['normal', 'suspicious', 'anomalous', 'dq_issue'],
    palette={'normal':'#2ca02c', 'suspicious':'#ff7f0e', 'anomalous':'#d62728', 'dq_issue':'#9467bd'},
    legend=False
)
plt.title('Category Distribution')
plt.show()""")

    # 10. Adversarial Edge Case Detection
    add_md("""# 10. Adversarial Edge Case Detection
Identify interviews with extreme or degenerate data: missing values, non-positive durations, zero entropy.""")

    add_code("""edge_condition = df.get('audit_missing_data', pd.Series(False, index=df.index)) == True

if 'V-01_total_interview_duration_ms' in df.columns:
    edge_condition = edge_condition | (df['V-01_total_interview_duration_ms'] <= 0)

if 'T-03_rt_entropy' in df.columns:
    edge_condition = edge_condition | (df['T-03_rt_entropy'] == 0)

edge_cases = df[edge_condition]
print("Edge Cases Detected:", len(edge_cases))
display(edge_cases.head() if not edge_cases.empty else "No edge cases matched.")""")

    # 11. Final Output
    add_md("""# 11. Final Output
Export the audit-enriched dataset with all recomputed flags, scores, and categories.""")

    add_code("""timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
output_path = os.path.join(PROJECT_ROOT, 'output', f'audit_results_{CURRENT_RUN_LABEL}_{timestamp}.csv')
os.makedirs(os.path.dirname(output_path), exist_ok=True)
df.to_csv(output_path, index=False)
print("Audit results saved to:", output_path)""")

    # 12. Correlation Analysis
    add_md("""# 12. Correlation Analysis
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

    # 13. Anomaly vs. Session Duration
    add_md("""# 13. Anomaly vs. Session Duration
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

    # 14. Section-Level Fatigue Analysis
    add_md("""# 14. Section-Level Fatigue Analysis
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
            hue='computed_category',
            ax=ax, 
            order=['normal', 'suspicious', 'anomalous', 'dq_issue'],
            hue_order=['normal', 'suspicious', 'anomalous', 'dq_issue'],
            palette={'normal':'#2ca02c', 'suspicious':'#ff7f0e', 'anomalous':'#d62728', 'dq_issue':'#9467bd'},
            dodge=False,
            legend=False
        )
        ax.set_title(f'{feat} by Category')
        ax.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.show()
else:
    print("S-Series parameters not available for Section-Level Fatigue Analysis.")""")

    # 15. Multidimensional Feature Pairplot
    add_md("""# 15. Multidimensional Feature Pairplot
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

    # Write the canonical notebook and remove the old duplicate if it still exists.
    notebook_dir = os.path.join(os.getcwd(), 'notebooks')
    os.makedirs(notebook_dir, exist_ok=True)

    notebook_path = os.path.join(notebook_dir, 'System_Audit_Report.ipynb')
    try:
        with open(notebook_path, 'w', encoding='utf-8') as f:
            json.dump(notebook, f, indent=2)
        print("Notebook created successfully at:", notebook_path)
    except Exception as e:
        print("ERROR saving notebook:", e)

    duplicate_path = os.path.join(notebook_dir, 'System_Audit_Report_Final.ipynb')
    if os.path.exists(duplicate_path):
        os.remove(duplicate_path)
        print("Removed duplicate notebook:", duplicate_path)

if __name__ == '__main__':
    create_audit_report_notebook()
