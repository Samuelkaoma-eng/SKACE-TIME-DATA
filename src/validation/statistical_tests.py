import pandas as pd
import numpy as np
import scipy.stats as stats
import statsmodels.api as sm
from typing import Dict, Any

def compare_groups(df: pd.DataFrame, feature_col: str, label_col: str) -> Dict[str, Any]:
    """
    Compare a continuous timing feature between two groups (e.g., high vs low quality).
    Runs both an independent t-test (assumes normality) and a Mann-Whitney U test (non-parametric).
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing interview-level features and quality labels.
    feature_col : str
        Name of the feature column (e.g., 'speed_index').
    label_col : str
        Name of the binary label column (where 1 might be problematic, 0 is good).
        
    Returns
    -------
    dict
        Dictionary containing test statistics and p-values.
    """
    group0 = df[df[label_col] == 0][feature_col].dropna()
    group1 = df[df[label_col] == 1][feature_col].dropna()
    
    if len(group0) == 0 or len(group1) == 0:
        return {'error': 'Insufficient data in one or both groups.'}
        
    t_stat, t_pval = stats.ttest_ind(group0, group1, equal_var=False)
    u_stat, u_pval = stats.mannwhitneyu(group0, group1, alternative='two-sided')
    
    return {
        'feature': feature_col,
        'group0_mean': float(group0.mean()),
        'group1_mean': float(group1.mean()),
        't_stat': float(t_stat),
        't_pval': float(t_pval),
        'u_stat': float(u_stat),
        'u_pval': float(u_pval)
    }

def run_logistic_regression(df: pd.DataFrame, feature_cols: list, label_col: str) -> Any:
    """
    Run a logistic regression using statsmodels to determine feature significance
    in predicting the binary quality label.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with feature columns and a target label.
    feature_cols : list
        List of timing feature column names to include in the model.
    label_col : str
        Target variable (0 or 1).
        
    Returns
    -------
    statsmodels.discrete.discrete_model.BinaryResultsWrapper
        Fitted statsmodels logistic regression results object.
    """
    # Drop rows with missing values in the variables of interest
    model_data = df[feature_cols + [label_col]].dropna()
    
    X = model_data[feature_cols]
    y = model_data[label_col]
    
    # Add constant for intercept
    X = sm.add_constant(X)
    
    # Fit the logistic regression model
    logit_model = sm.Logit(y, X)
    result = logit_model.fit(disp=0)
    
    return result
