import pandas as pd
import numpy as np
import scipy.stats as stats

def calculate_basic_timing(df: pd.DataFrame) -> dict:
    """
    Calculate mean, median, variance, and total duration for a single interview.
    
    Parameters
    ----------
    df : pd.DataFrame
        Standardized paradata DataFrame for a single interview.
        
    Returns
    -------
    dict
        Dictionary containing response time metrics.
    """
    if 'duration_ms' not in df.columns or df.empty:
        return {
            'mean_response_time_ms': np.nan,
            'median_response_time_ms': np.nan,
            'variance_response_time_ms': np.nan,
            'entropy_response_time': np.nan,
            'total_duration_ms': np.nan
        }
        
    durations = df['duration_ms'].dropna()
    
    if durations.empty:
        return {
            'mean_response_time_ms': np.nan,
            'median_response_time_ms': np.nan,
            'variance_response_time_ms': np.nan,
            'entropy_response_time': np.nan,
            'total_duration_ms': np.nan
        }

    # Calculate Shannon entropy by binning response times
    # This detects if responses are unnaturally identical (low entropy)
    if len(durations) > 2:
        # Bin into 1-second intervals up to the 95th percentile to handle outliers
        cap = durations.quantile(0.95)
        if cap == 0 or np.isnan(cap):
            entropy = 0.0
        else:
            bins = np.arange(0, cap + 1000, 1000)
            if len(bins) > 1:
                hist, _ = np.histogram(durations, bins=bins)
                entropy = float(stats.entropy(hist))
            else:
                entropy = 0.0
    else:
        entropy = 0.0

    return {
        'mean_response_time_ms': float(durations.mean()),
        'median_response_time_ms': float(durations.median()),
        'variance_response_time_ms': float(durations.var()) if len(durations) > 1 else 0.0,
        'entropy_response_time': entropy,
        'total_duration_ms': float(durations.sum())
    }

def calculate_speed_index(interview_duration: float, global_median_duration: float) -> float:
    """
    Calculate the speed index of a given interview relative to the global survey median.
    
    Speed Index = Interview Total Duration / Global Median Duration
    A value < 1 indicates the interview was faster than the median.
    
    Parameters
    ----------
    interview_duration : float
        Total duration of the specific interview.
    global_median_duration : float
        Median total duration across all interviews in the survey.
        
    Returns
    -------
    float
        The calculated speed index.
    """
    if np.isnan(interview_duration) or np.isnan(global_median_duration) or global_median_duration == 0:
        return np.nan
        
    return interview_duration / global_median_duration
