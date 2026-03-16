import pandas as pd
from typing import Dict

def correlation_importance(df: pd.DataFrame, feature_cols: list, label_col: str) -> pd.Series:
    """
    Calculate the point-biserial correlation (Pearson) between each continuous feature
    and the binary target label to rank them by importance.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame of features and labels.
    feature_cols : list
        List of continuous feature names.
    label_col : str
        Binary target label.
        
    Returns
    -------
    pd.Series
        Correlation coefficients sorted by absolute magnitude.
    """
    correlations = {}
    for col in feature_cols:
        if col in df.columns:
            corr = df[col].corr(df[label_col])
            correlations[col] = corr
            
    corr_series = pd.Series(correlations)
    
    # Sort by absolute correlation
    return corr_series.reindex(corr_series.abs().sort_values(ascending=False).index)

def calculate_effect_sizes(df: pd.DataFrame, feature_cols: list, label_col: str) -> pd.DataFrame:
    """
    Calculate Cohen's d effect size for each feature between the two groups defined
    by the label column.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame of features and labels.
    feature_cols : list
        List of continuous feature names.
    label_col : str
        Binary target label (0 and 1).
        
    Returns
    -------
    pd.DataFrame
        DataFrame with Cohen's d values for each feature.
    """
    effect_sizes = []
    
    for col in feature_cols:
        group0 = df[df[label_col] == 0][col].dropna()
        group1 = df[df[label_col] == 1][col].dropna()
        
        if len(group0) > 1 and len(group1) > 1:
            n0, n1 = len(group0), len(group1)
            var0, var1 = group0.var(), group1.var()
            
            # Pooled standard deviation
            pooled_std = (((n0 - 1) * var0 + (n1 - 1) * var1) / (n0 + n1 - 2)) ** 0.5
            
            if pooled_std > 0:
                d = (group1.mean() - group0.mean()) / pooled_std
            else:
                d = 0.0
                
            effect_sizes.append({'feature': col, 'cohens_d': d})
            
    res_df = pd.DataFrame(effect_sizes)
    if not res_df.empty:
        # Sort by magnitude of effect size
        res_df['abs_d'] = res_df['cohens_d'].abs()
        res_df = res_df.sort_values(by='abs_d', ascending=False).drop(columns=['abs_d'])
    
    return res_df
