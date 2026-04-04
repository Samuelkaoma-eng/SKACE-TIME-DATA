import pandas as pd
import numpy as np

class SurveyFeatureExtractor:
    """
    Extracts Survey-Level (V) timing features from the structured CIR dataframe.
    Calculates features V-01 to V-10 for the entire interview session.
    """
    
    def extract(self, cir_df: pd.DataFrame) -> dict:
        if cir_df.empty:
            return {}
            
        df = cir_df.sort_values('start_ms').copy()
        
        features = {}
        
        # V-01 total_interview_duration_ms
        if len(df) > 0:
            features['V-01_total_interview_duration_ms'] = df['end_ms'].max() - df['start_ms'].min()
        else:
            features['V-01_total_interview_duration_ms'] = 0
            
        # V-02 speed_trajectory_early, V-03 speed_trajectory_late, V-04 speed_trajectory_ratio
        n_events = len(df)
        if n_events >= 3:
            def calc_slice_speed(slice_df):
                n_fields = len(slice_df[slice_df['event_type'] == 'field_end'])
                if n_fields > 0:
                    delta = slice_df['end_ms'].max() - slice_df['start_ms'].min()
                    return delta / n_fields
                return slice_df['duration_ms'].mean() if not slice_df['duration_ms'].isna().all() else 0.0

            third = max(1, n_events // 3)
            early = df.iloc[:third]
            late = df.iloc[-third:]
            
            features['V-02_speed_trajectory_early'] = calc_slice_speed(early)
            features['V-03_speed_trajectory_late'] = calc_slice_speed(late)
            
            # Layer 1 Mathematical Integrity: handle divide-by-zero
            if features['V-02_speed_trajectory_early'] > 0:
                features['V-04_speed_trajectory_ratio'] = features['V-03_speed_trajectory_late'] / features['V-02_speed_trajectory_early']
            else:
                # Return None for undefined math, allowing AnomalyDetector to flag accurately
                features['V-04_speed_trajectory_ratio'] = None
        else:
            features['V-02_speed_trajectory_early'] = None
            features['V-03_speed_trajectory_late'] = None
            features['V-04_speed_trajectory_ratio'] = None
            
        # V-05 back_navigation_rate and V-06 back_navigation_total_count
        back_mask = df['event_type'].str.contains('back|backward|jump', case=False, na=False)
        backs = int(back_mask.sum())
        features['V-06_back_navigation_total_count'] = backs
        n_question_events = len(df[~back_mask])          # events that are actual questions
        features['V-05_back_navigation_rate'] = backs / n_question_events if n_question_events > 0 else 0

        # V-07 time_of_day_hour
        first_ms = df['start_ms'].min()
        if pd.notna(first_ms):
            dt = pd.to_datetime(first_ms, unit='ms')
            features['V-07_time_of_day_hour'] = dt.hour
            features['V-08_day_of_week'] = dt.dayofweek
        else:
            features['V-07_time_of_day_hour'] = np.nan
            features['V-08_day_of_week'] = np.nan

        # V-09 session_length_vs_median (Will be calculated at global level in controller)
        features['V-09_session_length_vs_median'] = np.nan

        # V-10 zero_back_nav_flag
        # BUG-H4 FIX: thesis definition = "no back-navigation across more than 20
        # CONSECUTIVE questions".  The old code just checked (backs==0 and n_events>20)
        # which misses interviews with one early back-nav then 21+ clean questions.
        # Correct approach: walk the event sequence and find the longest run of
        # question events without any back/jump event between them.
        max_consecutive = 0
        current_run = 0
        for evt in df['event_type']:
            if str(evt).lower() not in ('back', 'backward', 'jump'):
                current_run += 1
                max_consecutive = max(max_consecutive, current_run)
            else:
                current_run = 0
        features['V-10_zero_back_nav_flag'] = 1 if max_consecutive >= 20 else 0

        return features
