import pandas as pd
import numpy as np

def calculate_navigation_metrics(df: pd.DataFrame, straightline_threshold_ms: float = 1500) -> dict:
    """
    Calculate navigation-specific features like backtracking and straightlining.
    
    Parameters
    ----------
    df : pd.DataFrame
        Paradata DataFrame for a single interview.
    straightline_threshold_ms : float
        Threshold for considering a response an element of straightlining.
        
    Returns
    -------
    dict
        Dictionary with navigation metrics.
    """
    if df.empty or 'event_type' not in df.columns:
        return {
        'backtrack_count': 0,
        'forward_jump_count': 0,
        'screen_revisit_rate': 0.0,
        'straightlining_count': 0
    }
    
    backtrack_keywords = ['backward', 'back', 'jump_backward']
    forward_keywords = ['forward', 'skip', 'jump_forward']
    
    str_events = df['event_type'].astype(str).str.lower()
    
    backtrack_count = int(str_events.isin(backtrack_keywords).sum())
    forward_count = int(str_events.isin(forward_keywords).sum())
    
    # Screen revisit rate: number of duplicate occurrences of the same question node normalized
    revisit_rate = 0.0
    if 'question_name' in df.columns:
        valid_nodes = df['question_name'].dropna()
        total_views = len(valid_nodes)
        if total_views > 0:
            duplicates = total_views - len(valid_nodes.unique())
            revisit_rate = float(duplicates) / float(total_views)
    
    straightlining_count = 0
    if 'duration_ms' in df.columns:
        valid_responses = df[df['duration_ms'] > 0]
        straightlining_count = int((valid_responses['duration_ms'] < straightline_threshold_ms).sum())
        
    return {
        'backtrack_count': backtrack_count,
        'forward_jump_count': forward_count,
        'screen_revisit_rate': revisit_rate,
        'straightlining_count': straightlining_count
    }
