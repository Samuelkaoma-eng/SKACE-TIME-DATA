import pandas as pd
import numpy as np

class QuestionFeatureExtractor:
    """
    Extracts Question-Level (Q) timing features from the structured CIR dataframe.
    Calculates features Q-01 to Q-10 for each field_name.
    """
    
    def extract(self, cir_df: pd.DataFrame) -> pd.DataFrame:
        """
        Parameters:
            cir_df: CIR standardized dataframe for a single interview.
            
        Returns:
            pd.DataFrame indexed by field_name with columns Q-01 to Q-10.
        """
        q_features = []
        # Filter: Only process rows that correspond to actual question/field interactions.
        # Exclude 'unknown_field' and 'form_start/end' events which are administrative.
        valid_cir = cir_df[
            (~cir_df['field_name'].isin(['unknown_field', 'MainSection'])) & 
            (~cir_df['event_type'].isin(['form_start', 'form_end']))
        ]
        
        if valid_cir.empty:
            return pd.DataFrame()
            
        groups = valid_cir.groupby('field_name')
        
        for field, group in groups:
            group = group.sort_values('start_ms')
            
            # Q-10 / Q-01 Absolute Boundaries
            if len(group) >= 1:
                end_max = group['end_ms'].max()
                start_min = group['start_ms'].min()
                f2l = end_max - start_min if pd.notna(end_max) and pd.notna(start_min) else 0
            else:
                f2l = 0

            # Q-01 response_time_ms (Total duration on this question)
            # Bound absolutely to avoid overlapping SurveyCTO counts and zeroed ODK bounds.
            rt_ms = f2l
            
            # Q-02 time_to_first_interaction
            ttfi = group['duration_ms'].iloc[0] if not group.empty else 0
            
            # Q-03 edit_count
            edit_count = max(0, len(group) - 1)
            
            # Q-04 revisit_flag
            revisit_flag = 1 if edit_count > 0 else 0
            
            # Q-05 revisit_count
            revisit_count = edit_count # For CIR, revisits and edits are isomorphic without screen boundary differentiation
            
            # Q-06 field_completion_ratio (1.0 if visited, assume completed if duration > 0)
            fcr = 1.0 if rt_ms > 0 else 0.0
            
            # Q-07 idle_time_ms
            # Gaps between end of one event and start of another within this question
            idle_time = 0
            if len(group) > 1:
                gaps = group['start_ms'].values[1:] - group['end_ms'].values[:-1]
                idle_time = gaps[gaps > 0].sum()
                
            # Q-08 keystroke_count
            # Approximate by number of events on the field
            keystroke_count = len(group)
            
            # Q-09 constraint_trigger_count
            # Look for specific error/constraint event types
            ctc = len(group[group['event_type'].str.contains('error|constraint|invalid', case=False, na=False)])
            
            # Q-09 constraint_trigger_count
            ctc = len(group[group['event_type'].str.contains('error|constraint|invalid', case=False, na=False)])
                
            q_features.append({
                'field_name': field,
                'Q-01_response_time_ms': rt_ms,
                'Q-02_time_to_first_interaction': ttfi,
                'Q-03_edit_count': edit_count,
                'Q-04_revisit_flag': revisit_flag,
                'Q-05_revisit_count': revisit_count,
                'Q-06_field_completion_ratio': fcr,
                'Q-07_idle_time_ms': idle_time,
                'Q-08_keystroke_count': keystroke_count,
                'Q-09_constraint_trigger_count': ctc,
                'Q-10_first_to_last_interaction_duration': f2l
            })
            
        return pd.DataFrame(q_features).set_index('field_name')
