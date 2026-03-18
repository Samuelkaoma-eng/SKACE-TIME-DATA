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
            'mean_response_time': np.nan,
            'median_response_time': np.nan,
            'response_time_variance': np.nan,
            'min_response_time': np.nan,
            'max_response_time': np.nan,
            'response_time_entropy': np.nan,
            'response_time_skewness': np.nan,
            'response_time_kurtosis': np.nan,
            'total_duration': np.nan,
            'uniform_speed_score': np.nan
        }
        
    durations = df['duration_ms'].dropna()
    
    if len(durations) == 0:
        return {
            'mean_response_time': np.nan,
            'median_response_time': np.nan,
            'response_time_variance': np.nan,
            'min_response_time': np.nan,
            'max_response_time': np.nan,
            'response_time_entropy': np.nan,
            'response_time_skewness': np.nan,
            'response_time_kurtosis': np.nan,
            'total_duration': np.nan,
            'uniform_speed_score': np.nan
        }

    # Shannon entropy calculation
    entropy = 0.0
    if len(durations) > 2:
        cap = durations.quantile(0.95)
        if cap > 0 and not np.isnan(cap):
            bins = np.arange(0, cap + 1000, 1000)
            if len(bins) > 1:
                hist, _ = np.histogram(durations, bins=bins)
                entropy = float(stats.entropy(hist))

    # Skewness and Kurtosis require sufficient variance and n > 3
    variance = float(durations.var()) if len(durations) > 1 else 0.0
    uniform_speed_score = float(durations.std()) if len(durations) > 1 else 0.0
    
    if variance < 1e-6:
        skewness = 0.0 if len(durations) > 2 else np.nan
        kurtosis = 0.0 if len(durations) > 3 else np.nan
    else:
        skewness = float(stats.skew(durations)) if len(durations) > 2 else np.nan
        kurtosis = float(stats.kurtosis(durations)) if len(durations) > 3 else np.nan

    return {
        'mean_response_time': float(durations.mean()),
        'median_response_time': float(durations.median()),
        'response_time_variance': variance,
        'min_response_time': float(durations.min()),
        'max_response_time': float(durations.max()),
        'response_time_entropy': entropy,
        'response_time_skewness': skewness,
        'response_time_kurtosis': kurtosis,
        'total_duration': float(durations.sum()),
        'uniform_speed_score': uniform_speed_score
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
