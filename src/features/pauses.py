import pandas as pd
import numpy as np

def calculate_pauses(df: pd.DataFrame, pause_threshold_ms: float = 60000) -> dict:
    """
    Calculate the frequency and total duration of pauses within an interview.
    A pause can be detected in two ways depending on the survey tool:
    1. Explicit 'pause' or 'resume' events.
    2. Gaps between the end of one question and the start of the next 
       that exceed a given threshold.
       
    This function primarily relies on finding gaps between consecutive events.
    
    Parameters
    ----------
    df : pd.DataFrame
        Standardized paradata DataFrame for a single interview, ideally sorted by start_time.
    pause_threshold_ms : float
        The duration in milliseconds above which a gap is considered a pause.
        
    Returns
    -------
    dict
        Dictionary containing pause metrics.
    """
    if 'end_time' not in df.columns or 'start_time' not in df.columns or len(df) < 2:
        return {
            'pause_frequency': 0,
            'total_pause_duration_ms': 0.0
        }
        
    df_sorted = df.sort_values(by='start_time').copy()
    
    # Calculate gap between end of current event and start of next event
    df_sorted['next_start'] = df_sorted['start_time'].shift(-1)
    df_sorted['gap_ms'] = (df_sorted['next_start'] - df_sorted['end_time']).dt.total_seconds() * 1000
    
    # Identify gaps that exceed the threshold
    pauses = df_sorted[df_sorted['gap_ms'] >= pause_threshold_ms]['gap_ms']
    
    return {
        'pause_frequency': int(len(pauses)),
        'total_pause_duration_ms': float(pauses.sum()) if not pauses.empty else 0.0
    }
