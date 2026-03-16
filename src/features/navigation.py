import pandas as pd
import numpy as np

def calculate_navigation_metrics(df: pd.DataFrame, straightline_threshold_ms: float = 1500) -> dict:
    """
    Calculate navigation-specific features like backtracking and straightlining.
    
    Parameters
    ----------
    df : pd.DataFrame
        Standardized paradata DataFrame for a single interview.
    straightline_threshold_ms : float
        Threshold for considering a response an element of straightlining (e.g. < 1.5s).
        
    Returns
    -------
    dict
        Dictionary with navigation metrics.
    """
    if df.empty or 'event_type' not in df.columns:
        return {
            'backtrack_count': 0,
            'straightlining_count': 0
        }
    
    # Identify backwards navigation if using ODK or explicitly marked events
    # Or by tracking repeated node accesses.
    
    # Simplified approach for explicitly marked backwards events
    # In some logs this might be 'jump backward', 'backward', etc.
    backtrack_keywords = ['backward', 'back', 'jump_backward']
    
    is_backtrack = df['event_type'].astype(str).str.lower().isin(backtrack_keywords)
    backtrack_count = int(is_backtrack.sum())
    
    # For straightlining, we examine questions answered very quickly
    straightlining_count = 0
    if 'duration_ms' in df.columns:
        valid_responses = df[df['duration_ms'] > 0]
        # Number of responses below the straightlining threshold
        straightlining_count = int((valid_responses['duration_ms'] < straightline_threshold_ms).sum())
        
    return {
        'backtrack_count': backtrack_count,
        'straightlining_count': straightlining_count
    }
