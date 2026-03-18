import pandas as pd
import numpy as np
from scipy.stats import skew, kurtosis, entropy

class StatisticalFeatureExtractor:
    """
    Extracts Statistical-Level (T) timing features from the Question-Level dataframe.
    Calculates features T-01 to T-10 characterizing the distribution of response times.
    """
    
    def extract(self, q_features_df: pd.DataFrame) -> dict:
        features = {}
        
        if q_features_df.empty or 'Q-01_response_time_ms' not in q_features_df.columns:
            m = ['T-01_rt_variance', 'T-02_rt_iqr', 'T-03_rt_entropy', 'T-04_rt_skewness', 
                 'T-05_rt_kurtosis', 'T-06_rt_mean', 'T-07_rt_median', 'T-08_rt_cv', 
                 'T-09_rt_min', 'T-10_rt_max']
            for f in m:
                features[f] = 0.0
            return features
            
        rt = q_features_df['Q-01_response_time_ms'].dropna()
        rt = rt[rt > 0] # Filter out 0 durations for valid statistical calculations
        
        if len(rt) == 0:
            for f in ['T-01_rt_variance', 'T-02_rt_iqr', 'T-03_rt_entropy', 'T-04_rt_skewness', 
                      'T-05_rt_kurtosis', 'T-06_rt_mean', 'T-07_rt_median', 'T-08_rt_cv', 
                      'T-09_rt_min', 'T-10_rt_max']:
                features[f] = 0.0
            return features
            
        # T-01 rt_variance
        features['T-01_rt_variance'] = rt.var() if len(rt) > 1 else 0
        
        # T-02 rt_iqr
        q75, q25 = np.percentile(rt, [75 ,25])
        features['T-02_rt_iqr'] = q75 - q25
        
        # T-03 rt_entropy (Binned Shannon Entropy of response times)
        # We use a consistent binning strategy (1000ms bins) to detect fabrication.
        # This ensures that identical behaviors result in identical entropy across formats.
        max_val = max(10000, rt.max() + 1000)
        bins = np.arange(0, max_val, 1000)
        hist, _ = np.histogram(rt, bins=bins)
        
        # Calculate probabilities from histogram
        counts = hist[hist > 0]
        if len(counts) > 0:
            probs = counts / counts.sum()
            features['T-03_rt_entropy'] = entropy(probs, base=2)
        else:
            features['T-03_rt_entropy'] = 0.0
        
        # T-04 rt_skewness
        if len(rt) > 2 and features['T-01_rt_variance'] > 0:
            features['T-04_rt_skewness'] = skew(rt)
        else:
            features['T-04_rt_skewness'] = 0.0
        
        # T-05 rt_kurtosis
        if len(rt) > 3 and features['T-01_rt_variance'] > 0:
            features['T-05_rt_kurtosis'] = kurtosis(rt)
        else:
            features['T-05_rt_kurtosis'] = 0.0
        
        # T-06 rt_mean
        features['T-06_rt_mean'] = rt.mean()
        
        # T-07 rt_median
        features['T-07_rt_median'] = rt.median()
        
        # T-08 rt_cv (Coefficient of Variation)
        mean_rt = features['T-06_rt_mean']
        std_rt = rt.std() if len(rt) > 1 else 0
        features['T-08_rt_cv'] = std_rt / mean_rt if mean_rt > 0 else 0.0
        
        # T-09 rt_min
        features['T-09_rt_min'] = rt.min()
        
        # T-10 rt_max
        features['T-10_rt_max'] = rt.max()
        
        return features
