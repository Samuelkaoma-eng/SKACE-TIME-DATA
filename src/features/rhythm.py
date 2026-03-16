import pandas as pd
import numpy as np

def calculate_rhythm_metrics(df: pd.DataFrame, window_size: int = 5) -> dict:
    """
    Calculate interview rhythm and irregularity features.
    
    Rhythm can be measured as the variability in response times over a rolling window.
    High variability might indicate a struggling respondent, while low variability
    might indicate rushing or an engaged, smooth flow.
    
    Parameters
    ----------
    df : pd.DataFrame
        Standardized paradata DataFrame for a single interview.
    window_size : int
        Size of the rolling window for variance calculations.
        
    Returns
    -------
    dict
        Dictionary containing rhythm metrics.
    """
    if 'duration_ms' not in df.columns or len(df.dropna(subset=['duration_ms'])) < window_size:
        return {
            'rhythm_variance_mean': np.nan,
            'rhythm_variance_max': np.nan
        }
        
    # Sort by time if possible
    if 'start_time' in df.columns:
        df_sorted = df.sort_values(by='start_time')
    else:
        df_sorted = df
        
    durations = df_sorted['duration_ms'].dropna()
    
    # Rolling variance of response times
    rolling_var = durations.rolling(window=window_size).var().dropna()
    
    if rolling_var.empty:
        return {
            'rhythm_variance_mean': np.nan,
            'rhythm_variance_max': np.nan
        }
        
    return {
        'rhythm_variance_mean': float(rolling_var.mean()),
        'rhythm_variance_max': float(rolling_var.max())
    }
