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
        ].copy()

        if valid_cir.empty:
            return pd.DataFrame()

        # BUG-H2 FIX: Pre-compute revisit flags at the interview level.
        # A revisit occurs when a field_name appears NON-CONSECUTIVELY in the
        # time-sorted CIR sequence —  i.e. the user left a field and came back.
        # This is categorically different from edit_count (multiple events during
        # a single continuous stay on a field).
        sorted_cir = valid_cir.sort_values('start_ms')
        field_sequence = sorted_cir['field_name'].tolist()
        revisit_set = set()      # fields that were genuinely revisited
        revisit_counts = {}      # how many times each field was revisited
        seen_fields = set()
        prev_field = None
        for fname in field_sequence:
            if fname != prev_field:          # field transition
                if fname in seen_fields:     # returning to a previously seen field
                    revisit_set.add(fname)
                    revisit_counts[fname] = revisit_counts.get(fname, 0) + 1
                seen_fields.add(fname)
                prev_field = fname

        groups = valid_cir.groupby('field_name')

        for field, group in groups:
            group = group.sort_values('start_ms')

            # Q-10 / Q-01 Absolute Boundaries
            # Exclude navigation events (jump/back) from the RT window.
            # A jump event can share the same field_name as the preceding question but
            # occurs 300-800ms AFTER the question response, inflating the window and
            # introducing artificial variance that masks flag_uniform_timing on
            # constant-RT (disengaged/fabricated) profiles.
            nav_mask = group['event_type'].str.contains(
                'jump|back|backward|forward|skip', case=False, na=False
            )
            question_events = group[~nav_mask]
            if not question_events.empty:
                end_max = question_events['end_ms'].max()
                start_min = question_events['start_ms'].min()
                f2l = end_max - start_min if pd.notna(end_max) and pd.notna(start_min) else 0
            elif len(group) >= 1:
                # All events are navigation — use full window as fallback
                end_max = group['end_ms'].max()
                start_min = group['start_ms'].min()
                f2l = end_max - start_min if pd.notna(end_max) and pd.notna(start_min) else 0
            else:
                f2l = 0

            # Q-01 response_time_ms (Total time on this question, navigation-events excluded)
            rt_ms = f2l

            # Q-02 time_to_first_interaction
            # Definition (thesis Table 3): elapsed time from field DISPLAY to first user input.
            # Ideal: duration from 'field_start' event to first 'field_end' event.
            # If 'field_start' events exist in the CIR, use the proper boundary;
            # otherwise fall back to the duration of the first event (best-effort approximation).
            start_events = group[group['event_type'].isin(['field_start', 'question-start'])]
            end_events   = group[group['event_type'].isin(['field_end',   'question-end'])]
            if not start_events.empty and not end_events.empty:
                ttfi = end_events['start_ms'].iloc[0] - start_events['start_ms'].iloc[0]
                ttfi = max(0, ttfi)
            else:
                # Fallback: duration of first recorded event on this field.
                # Not a true TTFI but the closest available approximation from CIR.
                ttfi = group['duration_ms'].iloc[0] if not group.empty else 0

            # Q-03 edit_count: number of ADDITIONAL events on same field during same visit.
            # Multiple consecutive events on a field indicate the user is editing their response.
            edit_count = max(0, len(group) - 1)

            # Q-04 revisit_flag: field was returned to after leaving (sequence-based detection).
            # BUG-H2 FIX: distinct from edit_count — a revisit requires leaving and coming back.
            revisit_flag = 1 if field in revisit_set else 0

            # Q-05 revisit_count: number of times the field was re-entered after leaving.
            revisit_count = revisit_counts.get(field, 0)

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
            # BUG-H3 FIX: was computed twice (duplicate lines 74-77), now computed once.
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
