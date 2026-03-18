import pandas as pd
import numpy as np

def calculate_rhythm_metrics(df: pd.DataFrame, window_size: int = 5) -> dict:
    """
    Calculate rhythm and irregularity features over rolling windows.
    
    Parameters
    ----------
    df : pd.DataFrame
        Paradata DataFrame for a single interview.
    window_size : int
        Size of the rolling window for variance calculations.
        
    Returns
    -------
    dict
        Dictionary containing rhythm metrics.
    """
    if 'duration_ms' not in df.columns or len(df.dropna(subset=['duration_ms'])) < window_size:
        return {
            'rolling_variance_mean': np.nan,
            'rolling_variance_max': np.nan,
            'straightlining_duration': 0.0
        }
        
    df_sorted = df.sort_values(by='start_time') if 'start_time' in df.columns else df
    durations = df_sorted['duration_ms'].dropna()
    
    rolling_var = durations.rolling(window=window_size).var().dropna()
    
    # Straightlining duration: Time spent repeatedly answering < 1500ms
    straightlining_mask = durations < 1500
    straightlining_dur = float(durations[straightlining_mask].sum()) if straightlining_mask.any() else 0.0
    
    if rolling_var.empty:
        return {
            'rolling_variance_mean': np.nan,
            'rolling_variance_max': np.nan,
            'straightlining_duration': straightlining_dur
        }
        
    return {
        'rolling_variance_mean': float(rolling_var.mean()),
        'rolling_variance_max': float(rolling_var.max()),
        'straightlining_duration': straightlining_dur
    }
