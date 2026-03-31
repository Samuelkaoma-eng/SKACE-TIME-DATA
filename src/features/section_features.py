import pandas as pd
import numpy as np

class SectionFeatureExtractor:
    """
    Extracts Section-Level (S) timing features from the structured CIR dataframe.
    Calculates features S-01 to S-10.
    Infers sections from prefixes on the field_name (e.g., matching split strings).
    """
    
    def extract(self, cir_df: pd.DataFrame, q_features_df: pd.DataFrame) -> pd.DataFrame:
        if cir_df.empty:
            return pd.DataFrame()
            
        # Infer section by grabbing string before first underscore or using 'Main' if none
        cir_df = cir_df.copy()
        cir_df['section_name'] = cir_df['field_name'].apply(
            lambda x: str(x).split('_')[0] if '_' in str(x) else 'MainSection'
        )
        
        # Pre-compute the max fields in any single section for S-10 denominator
        section_field_counts = {}
        for sec_name, sec_grp in cir_df.groupby('section_name'):
            section_field_counts[sec_name] = sec_grp['field_name'].nunique()
        max_fields_any_section = max(section_field_counts.values()) if section_field_counts else 1

        s_features = []
        groups = cir_df.groupby('section_name')
        
        for section, group in groups:
            group = group.sort_values('start_ms')
            
            # Extract section specific questions from q_features_df
            section_questions = group['field_name'].unique()
            if q_features_df.empty:
                q_sub = pd.DataFrame()
            else:
                q_sub = q_features_df[q_features_df.index.isin(section_questions)]
            
            # S-01 mean_section_pace
            pace = q_sub['Q-01_response_time_ms'].mean() if not q_sub.empty else 0
            
            # S-02 section_duration_ms
            end_max = group['end_ms'].max()
            start_min = group['start_ms'].min()
            duration = end_max - start_min if pd.notna(end_max) and pd.notna(start_min) else 0
            
            # S-03 within_section_variance
            variance = q_sub['Q-01_response_time_ms'].var() if len(q_sub) > 1 else 0
            
            # Calculate Pauses within section
            pauses = np.array([])
            if len(group) > 1:
                gaps = group['start_ms'].values[1:] - group['end_ms'].values[:-1]
                pauses = gaps[gaps > 0]
                
            # S-05 pause_count_5s
            p_5s = len(pauses[pauses > 5000]) if len(pauses) > 0 else 0
            
            # S-06 pause_count_30s
            p_30s = len(pauses[pauses > 30000]) if len(pauses) > 0 else 0
            
            # S-07 mean_pause_duration_ms
            mean_p = pauses.mean() if len(pauses) > 0 else 0
            
            # S-08 max_pause_duration_ms
            max_p = pauses.max() if len(pauses) > 0 else 0
            
            # S-09 back_nav_count_section
            # Defined by backward jump events
            back_nav = len(group[group['event_type'].str.contains('back|backward', case=False, na=False)])
            
            # S-10 section_completion_rate
            # BUG-8 FIX: Within-dataset approximation.
            # Since no master questionnaire schema is available, we use:
            #   fields_visited_in_section / max_fields_in_any_section_across_dataset
            # This yields 1.0 for the most-visited section and < 1.0 for shorter/skipped sections,
            # giving genuine discriminative variance across the dataset (thesis §1.3 Obj 3).
            fields_visited = group['field_name'].nunique()
            denom = max(max_fields_any_section, 1)
            comp_rate = min(1.0, fields_visited / denom)
            
            s_features.append({
                'section_name': section,
                'S-01_mean_section_pace': pace,
                'S-02_section_duration_ms': duration,
                'S-03_within_section_variance': variance,
                # S-04 calculated after loop over all sections
                'S-05_pause_count_5s': p_5s,
                'S-06_pause_count_30s': p_30s,
                'S-07_mean_pause_duration_ms': mean_p,
                'S-08_max_pause_duration_ms': max_p,
                'S-09_back_nav_count_section': back_nav,
                'S-10_section_completion_rate': comp_rate
            })
            
        df_sec = pd.DataFrame(s_features).set_index('section_name')
        
        # S-04 section_to_section_pace_ratio
        if not df_sec.empty:
            global_pace = q_features_df['Q-01_response_time_ms'].mean() if not q_features_df.empty else 1.0
            global_pace = global_pace if global_pace > 0 else 1.0
            df_sec['S-04_section_to_section_pace_ratio'] = df_sec['S-01_mean_section_pace'] / global_pace
            
        return df_sec
