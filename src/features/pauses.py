import pandas as pd
import numpy as np

def calculate_pauses(df: pd.DataFrame, pause_threshold_ms: float = 60000) -> dict:
    """
    Calculate the frequency and duration of pauses within an interview.
    
    Parameters
    ----------
    df : pd.DataFrame
        Paradata DataFrame for a single interview.
    pause_threshold_ms : float
        Duration in milliseconds above which a gap is considered a pause.
        
    Returns
    -------
    dict
        Dictionary containing pause metrics.
    """
    if 'end_time' not in df.columns or 'start_time' not in df.columns or len(df) < 2:
        return {
        'pause_count': 0,
        'total_pause_duration': 0.0,
        'average_pause_length': 0.0
    }
    
    df_sorted = df.sort_values(by='start_time').copy()
    df_sorted = df_sorted.assign(next_start=df_sorted['start_time'].shift(-1))
    df_sorted = df_sorted.assign(
        gap_ms=(df_sorted['next_start'] - df_sorted['end_time']).dt.total_seconds() * 1000
    )
    
    pauses = df_sorted[df_sorted['gap_ms'] >= pause_threshold_ms]['gap_ms']
    
    pause_count = int(len(pauses))
    total_pause = float(pauses.sum()) if pause_count > 0 else 0.0
    avg_pause = total_pause / pause_count if pause_count > 0 else 0.0
    
    return {
        'pause_count': pause_count,
        'total_pause_duration': total_pause,
        'average_pause_length': avg_pause
    }
