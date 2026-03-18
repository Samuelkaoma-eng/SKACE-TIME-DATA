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
        # Note: Behavioral flags can still be set, but is_anomalous_behavior only triggers for DQ=0
        
        # Temporal Bounds
        if 'V-01_total_interview_duration_ms' in df.columns:
            dur = df['V-01_total_interview_duration_ms']
            med = dur.median()
            if med > 0:
                df.loc[dur < (med * 0.3), 'flag_too_fast'] = 1
                df.loc[dur > (med * 10), 'flag_too_slow'] = 1
            
            # Absolute max thresholds
            df.loc[dur > 1800000, 'flag_too_slow'] = 1
            df.loc[dur > 1800000, 'flag_max_duration'] = 1

            if len(df) > 3:
                Q1, Q3 = dur.quantile(0.25), dur.quantile(0.75)
                IQR = Q3 - Q1
                df.loc[(dur < Q1 - 1.5*IQR) | (dur > Q3 + 1.5*IQR), 'flag_iqr_duration'] = 1

        # Uniformity & Entropy Linkage
        if 'T-03_rt_entropy' in df.columns:
            # Smart Fraud often has entropy < 1.0 (natural is 1.5 - 2.5)
            df.loc[df['T-03_rt_entropy'] < 1.0, 'flag_low_entropy'] = 1
            df.loc[df['T-03_rt_entropy'] == 0, 'flag_low_entropy'] = 1
            
        if 'T-08_rt_cv' in df.columns:
            df.loc[df['T-08_rt_cv'] < self.uniform_timing_cv, 'flag_uniform_timing'] = 1


        # Navigation patterns
        if 'V-06_back_navigation_total_count' in df.columns:
            # Row-level straight-lining
            df.loc[df['V-06_back_navigation_total_count'] == 0, 'flag_zero_back_nav'] = 1
            # High Back-Nav (Confused/Correction Fraud)
            if 'V-05_back_navigation_rate' in df.columns:
                df.loc[df['V-05_back_navigation_rate'] > 0.4, 'flag_high_back_nav'] = 1

        # --- LAYER 4: DATASET-LEVEL INTELLIGENCE (Removed per user request) ---
        # df = self.detect_population_patterns(df)

        # --- DATA QUALITY TRIGGER ---
        # Trigger if Layers 1-2 fail OR if metrics are degenerate
        df['is_data_quality_issue'] = (
            df['flag_missing_data'] | 
            df['flag_invalid_ratio'] | 
            df['flag_inconsistent_metrics']
        ).astype(int)
        
        # Extreme Temporal DQ (1 hour or more)
        if 'V-01_total_interview_duration_ms' in df.columns:
            df.loc[df['V-01_total_interview_duration_ms'] >= 3600000, 'is_data_quality_issue'] = 1

        # --- EXPLAINABLE ANOMALY SCORING ---
        # Formula: Transparent & Weighted
        # Adjusted for requested scale: 0-5 Normal, 6-9 Suspicious, 10-15 Anomaly
        df['anomaly_score'] = (
            4 * df['flag_invalid_ratio'].fillna(0) +
            4 * df['flag_inconsistent_metrics'].fillna(0) +
            4 * df['flag_uniform_timing'].fillna(0) +
            3 * df['flag_low_entropy'].fillna(0) +
            3 * df['flag_too_fast'].fillna(0) +
            3 * df['flag_max_duration'].fillna(0) +
            2 * df['flag_zero_back_nav'].fillna(0) +
            1 * df['flag_high_back_nav'].fillna(0) +
            1 * df['flag_rule_pause'].fillna(0)
        )
        
        # 3-Tier Categorical Scaling
        # 0 - 5  : normal (or minor_dq if DQ)
        # 6 - 9  : suspicious
        # 10 - 15: strong_anomaly
        df['anomaly_category'] = pd.cut(
            df['anomaly_score'], 
            bins=[-np.inf, 5, 9, np.inf], 
            labels=['normal', 'suspicious', 'strong_anomaly']
        ).astype(str)
        
        # We classify suspicious and strong_anomaly as behavior flags
        df['is_anomalous_behavior'] = (df['anomaly_score'] >= 6).astype(int)
        
        # DQ isolation: Behavior only applies to Clean logs
        df.loc[df['is_data_quality_issue'] == 1, 'is_anomalous_behavior'] = 0
        df.loc[df['is_data_quality_issue'] == 1, 'anomaly_category'] = 'minor_dq'
        
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
