import pandas as pd
import numpy as np

class AnomalyDetector:
    """
    Implements IQR-based and rule-based anomaly detection on the final combined
    feature dataset.
    """
    
    def __init__(
        self,
        uniform_timing_cv=0.1,
        behavior_score_threshold=3,
        anomalous_score_threshold=5,
        too_fast_ms=6000,
        too_slow_ms=3600000,
        low_entropy_threshold=0.5,
        low_variance_threshold=10,
        high_back_nav_rate_threshold=0.5,
    ):
        self.uniform_timing_cv = uniform_timing_cv
        self.behavior_score_threshold = behavior_score_threshold
        self.anomalous_score_threshold = anomalous_score_threshold
        self.too_fast_ms = too_fast_ms
        self.too_slow_ms = too_slow_ms
        self.low_entropy_threshold = low_entropy_threshold
        self.low_variance_threshold = low_variance_threshold
        self.high_back_nav_rate_threshold = high_back_nav_rate_threshold
        
    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Evaluates the combined feature dataset for data quality issues and behavioral anomalies.
        """
        if df.empty:
            return df
            
        df = df.copy()
        
        # Initialize ALL diagnostic flags to 0.
        # flag_population_pattern was removed (BUG-H6): it was initialised but
        # never computed anywhere in detect(), so it was always 0 and contributed
        # nothing to anomaly_score or categorisation.
        diag_flags = [
            'flag_invalid_ratio', 'flag_missing_data', 'flag_inconsistent_metrics',
            'flag_too_fast', 'flag_too_slow',
            'flag_zero_back_nav', 'flag_low_entropy', 'flag_uniform_timing',
            'flag_rule_pause', 'flag_iqr_duration',
            'flag_iqr_rt_mean', 'flag_iqr_entropy', 'flag_iqr_variance',
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
        
        # Temporal Bounds
        if 'V-01_total_interview_duration_ms' in df.columns:
            dur = df['V-01_total_interview_duration_ms']
            df.loc[dur < self.too_fast_ms, 'flag_too_fast'] = 1
            df.loc[dur > self.too_slow_ms, 'flag_too_slow'] = 1
            
            # Additional IQR Audit Flag
            if len(df) > 3:
                Q1, Q3 = dur.quantile(0.25), dur.quantile(0.75)
                IQR = Q3 - Q1
                df.loc[(dur < Q1 - 1.5*IQR) | (dur > Q3 + 2.5*IQR), 'flag_iqr_duration'] = 1

                if 'T-06_rt_mean' in df.columns:
                    mean_vals = df['T-06_rt_mean']
                    q1m, q3m = mean_vals.quantile(0.25), mean_vals.quantile(0.75)
                    iqr_mean = q3m - q1m
                    if iqr_mean > 0:
                        df.loc[(mean_vals < q1m - 1.5*iqr_mean) | (mean_vals > q3m + 3.0*iqr_mean), 'flag_iqr_rt_mean'] = 1

                if 'T-03_rt_entropy' in df.columns:
                    entropy_vals = df['T-03_rt_entropy']
                    q1e, q3e = entropy_vals.quantile(0.25), entropy_vals.quantile(0.75)
                    iqr_entropy = q3e - q1e
                    if iqr_entropy > 0:
                        df.loc[(entropy_vals < q1e - 1.5*iqr_entropy) | (entropy_vals > q3e + 1.5*iqr_entropy), 'flag_iqr_entropy'] = 1

                if 'T-01_rt_variance' in df.columns:
                    var_vals = df['T-01_rt_variance']
                    q1v, q3v = var_vals.quantile(0.25), var_vals.quantile(0.75)
                    iqr_variance = q3v - q1v
                    if iqr_variance > 0:
                        df.loc[(var_vals < q1v - 1.5*iqr_variance) | (var_vals > q3v + 1.5*iqr_variance), 'flag_iqr_variance'] = 1

        # Entropy & Uniformity
        if 'T-03_rt_entropy' in df.columns:
            df.loc[df['T-03_rt_entropy'] < self.low_entropy_threshold, 'flag_low_entropy'] = 1
            
        if 'T-01_rt_variance' in df.columns:
            df.loc[df['T-01_rt_variance'] < self.low_variance_threshold, 'flag_uniform_timing'] = 1

        # Navigation patterns
        if 'V-06_back_navigation_total_count' in df.columns:
            df.loc[df['V-06_back_navigation_total_count'] == 0, 'flag_zero_back_nav'] = 1
            if 'V-05_back_navigation_rate' in df.columns:
                df.loc[df['V-05_back_navigation_rate'] > self.high_back_nav_rate_threshold, 'flag_high_back_nav'] = 1

        # Pause-oriented disengagement signal
        pause_flag = pd.Series(False, index=df.index)
        if 'S-06_pause_count_30s' in df.columns:
            pause_flag = pause_flag | (df['S-06_pause_count_30s'] >= 2)
        if 'S-08_max_pause_duration_ms' in df.columns:
            pause_flag = pause_flag & (df['S-08_max_pause_duration_ms'] >= 280000)
        df.loc[pause_flag, 'flag_rule_pause'] = 1

        # --- DATA QUALITY TRIGGER ---
        df['is_data_quality_issue'] = (
            df['flag_missing_data'] | 
            df['flag_invalid_ratio'] | 
            df['flag_inconsistent_metrics'] |
            (df['V-01_total_interview_duration_ms'] <= 0 if 'V-01_total_interview_duration_ms' in df.columns else False)
        ).astype(int)

        # --- EXPLAINABLE ANOMALY SCORING (User Weights) ---
        # Formula prioritizes clear behavioral risk, plus robust outlier signals.
        df['anomaly_score'] = (
            3 * df['flag_too_fast'].fillna(0) +
            2 * df['flag_too_slow'].fillna(0) +
            2 * df['flag_low_entropy'].fillna(0) +
            2 * df['flag_uniform_timing'].fillna(0) +
            1 * df['flag_high_back_nav'].fillna(0) +
            1 * df['flag_iqr_duration'].fillna(0) +
            2 * df['flag_iqr_rt_mean'].fillna(0) +
            1 * df['flag_iqr_entropy'].fillna(0) +
            1 * df['flag_rule_pause'].fillna(0) +
            3 * df['flag_invalid_ratio'].fillna(0)
        )
        
        # User Categorization
        def get_category(row):
            if row['is_data_quality_issue'] == 1:
                return "dq_issue"
            elif row['anomaly_score'] >= self.anomalous_score_threshold:
                return "anomalous"
            elif row['anomaly_score'] >= self.behavior_score_threshold:
                return "suspicious"
            else:
                return "normal"

        df['anomaly_category'] = df.apply(get_category, axis=1)
        df['is_anomalous_behavior'] = (df['anomaly_score'] >= self.behavior_score_threshold).astype(int)
        df['is_anomalous'] = (df['is_anomalous_behavior'] | df['is_data_quality_issue']).astype(int)

        # Report-friendly summary fields
        df['iqr_flags'] = (
            df['flag_iqr_duration'].fillna(0) +
            df['flag_iqr_rt_mean'].fillna(0) +
            df['flag_iqr_entropy'].fillna(0) +
            df['flag_iqr_variance'].fillna(0)
        ).astype('Int64')

        df['rule_flags'] = (
            df['flag_too_fast'].fillna(0) +
            df['flag_too_slow'].fillna(0) +
            df['flag_zero_back_nav'].fillna(0) +
            df['flag_low_entropy'].fillna(0) +
            df['flag_uniform_timing'].fillna(0) +
            df['flag_high_back_nav'].fillna(0) +
            df['flag_rule_pause'].fillna(0)
        ).astype('Int64')

        flag_cols = [c for c in diag_flags if c in df.columns]
        def join_flags(row):
            active = [c for c in flag_cols if row[c] == 1]
            return ','.join(active)

        df['flagged_features'] = df.apply(join_flags, axis=1)

        def get_status(row):
            if row['is_data_quality_issue'] == 1 or row['anomaly_score'] >= self.anomalous_score_threshold:
                return 'FLAGGED'
            if row['anomaly_score'] >= self.behavior_score_threshold:
                return 'REVIEW'
            return 'CLEAN'

        df['status'] = df.apply(get_status, axis=1)
        
        # Cleanup: Standardize Flag Types to Int64 (Nullable Integer) to prevent 1.0/0.0
        for f in diag_flags:
            if f in df.columns:
                df[f] = df[f].astype('Int64')
        df['is_data_quality_issue'] = df['is_data_quality_issue'].astype('Int64')
        df['is_anomalous_behavior'] = df['is_anomalous_behavior'].astype('Int64')
        df['is_anomalous'] = df['is_anomalous'].astype('Int64')
        df['anomaly_score'] = df['anomaly_score'].astype('Int64')
        df['iqr_flags'] = df['iqr_flags'].astype('Int64')
        df['rule_flags'] = df['rule_flags'].astype('Int64')
        
        return df
