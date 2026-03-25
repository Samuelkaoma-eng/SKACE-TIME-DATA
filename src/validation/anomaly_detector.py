import pandas as pd
import numpy as np

class AnomalyDetector:
    """
    Implements IQR-based and rule-based anomaly detection on the final combined
    feature dataset.
    """
    
    def __init__(self, uniform_timing_cv=0.1):
        self.uniform_timing_cv = uniform_timing_cv
        
    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Evaluates the combined feature dataset for data quality issues and behavioral anomalies.
        """
        if df.empty:
            return df
            
        df = df.copy()
        
        # Initialize ALL diagnostic flags (Harmonized with User Expectations)
        diag_flags = [
            'flag_invalid_ratio', 'flag_missing_data', 'flag_inconsistent_metrics',
            'flag_too_fast', 'flag_too_slow', 'flag_max_duration',
            'flag_zero_back_nav', 'flag_low_entropy', 'flag_uniform_timing',
            'flag_rule_pause', 'flag_population_pattern', 'flag_iqr_duration',
            'flag_high_back_nav'
        ]
        for f in diag_flags:
            df[f] = 0

        # --- LAYER 1: INPUT & METADATA VALIDATION (DQ TRIGGER) ---
        # Detect mathematical invalidity (Undefined Ratios)
        if 'V-04_speed_trajectory_ratio' in df.columns:
            # Explicitly check for NaN/None and catch zero-denominator from parser
            df.loc[df['V-04_speed_trajectory_ratio'].isna(), 'flag_invalid_ratio'] = 1
            
        # Detect Missing Core Data (T-Series)
        if 'T-06_rt_mean' in df.columns:
            # If mean is 0 or NaN but duration exists, the data is degenerate
            df.loc[(df['T-06_rt_mean'].isna()) | (df['T-06_rt_mean'] == 0), 'flag_missing_data'] = 1

        # Check for impossible values (e.g. negative time)
        if 'V-07_time_of_day_hour' in df.columns:
            df.loc[df['V-07_time_of_day_hour'] < 0, 'flag_inconsistent_metrics'] = 1
            
        if 'V-01_total_interview_duration_ms' in df.columns:
            df.loc[df['V-01_total_interview_duration_ms'] < 0, 'flag_inconsistent_metrics'] = 1

        # --- LAYER 2: FEATURE INTEGRITY CHECKS ---
        # Validate relationships between features
        if all(c in df.columns for c in ['T-10_rt_max', 'T-09_rt_min']):
            df.loc[df['T-10_rt_max'] < df['T-09_rt_min'], 'flag_inconsistent_metrics'] = 1
            
        if all(c in df.columns for c in ['S-02_section_duration_ms', 'Q-01_response_time_ms']):
            # Section duration must be >= mean question response time
            df.loc[df['S-02_section_duration_ms'] < df['Q-01_response_time_ms'], 'flag_inconsistent_metrics'] = 1
            
        if all(c in df.columns for c in ['Q-07_idle_time_ms', 'V-01_total_interview_duration_ms']):
            # Idle time cannot exceed total duration
            df.loc[df['Q-07_idle_time_ms'] > df['V-01_total_interview_duration_ms'], 'flag_inconsistent_metrics'] = 1

        # --- LAYER 3: BEHAVIORAL ANALYSIS (CLEAN LOGS ONLY) ---
        
        # Temporal Bounds (User Rule: Too Fast < 5000ms, Too Slow > 3600000ms)
        if 'V-01_total_interview_duration_ms' in df.columns:
            dur = df['V-01_total_interview_duration_ms']
            df.loc[dur < 5000, 'flag_too_fast'] = 1
            df.loc[dur > 3600000, 'flag_too_slow'] = 1
            
            # Additional IQR Audit Flag
            if len(df) > 3:
                Q1, Q3 = dur.quantile(0.25), dur.quantile(0.75)
                IQR = Q3 - Q1
                df.loc[(dur < Q1 - 1.5*IQR) | (dur > Q3 + 1.5*IQR), 'flag_iqr_duration'] = 1

        # Entropy & Uniformity (User Rule: Entropy < 0.5, Variance < 10)
        if 'T-03_rt_entropy' in df.columns:
            df.loc[df['T-03_rt_entropy'] < 0.5, 'flag_low_entropy'] = 1
            
        if 'T-01_rt_variance' in df.columns:
            df.loc[df['T-01_rt_variance'] < 10, 'flag_uniform_timing'] = 1

        # Navigation patterns (User Rule: Back-Nav Rate > 0.5, Count == 0)
        if 'V-06_back_navigation_total_count' in df.columns:
            df.loc[df['V-06_back_navigation_total_count'] == 0, 'flag_zero_back_nav'] = 1
            if 'V-05_back_navigation_rate' in df.columns:
                df.loc[df['V-05_back_navigation_rate'] > 0.5, 'flag_high_back_nav'] = 1

        # --- DATA QUALITY TRIGGER ---
        df['is_data_quality_issue'] = (
            df['flag_missing_data'] | 
            df['flag_invalid_ratio'] | 
            df['flag_inconsistent_metrics'] |
            (df['V-01_total_interview_duration_ms'] <= 0 if 'V-01_total_interview_duration_ms' in df.columns else False)
        ).astype(int)

        # --- EXPLAINABLE ANOMALY SCORING (User Weights) ---
        # Formula: fast*3, slow*2, entropy*2, uniform*2, back_nav*1, invalid_ratio*3
        df['anomaly_score'] = (
            3 * df['flag_too_fast'].fillna(0) +
            2 * df['flag_too_slow'].fillna(0) +
            2 * df['flag_low_entropy'].fillna(0) +
            2 * df['flag_uniform_timing'].fillna(0) +
            1 * df['flag_high_back_nav'].fillna(0) +
            3 * df['flag_invalid_ratio'].fillna(0)
        )
        
        # User Categorization: 0-3 Normal, 4-7 Suspicious, 8-15 Anomalous
        def get_category(row):
            if row['is_data_quality_issue'] == 1:
                return "dq_issue"
            elif row['anomaly_score'] >= 8:
                return "anomalous"
            elif row['anomaly_score'] >= 4:
                return "suspicious"
            else:
                return "normal"

        df['anomaly_category'] = df.apply(get_category, axis=1)
        df['is_anomalous_behavior'] = (df['anomaly_score'] >= 4).astype(int)
        df['is_anomalous'] = (df['is_anomalous_behavior'] | df['is_data_quality_issue']).astype(int)
        
        # Cleanup: Standardize Flag Types to Int64 (Nullable Integer) to prevent 1.0/0.0
        for f in diag_flags:
            if f in df.columns:
                df[f] = df[f].astype('Int64')
        df['is_data_quality_issue'] = df['is_data_quality_issue'].astype('Int64')
        df['is_anomalous_behavior'] = df['is_anomalous_behavior'].astype('Int64')
        df['is_anomalous'] = df['is_anomalous'].astype('Int64')
        df['anomaly_score'] = df['anomaly_score'].astype('Int64')
        
        return df
