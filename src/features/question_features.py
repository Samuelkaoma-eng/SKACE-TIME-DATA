import numpy as np
import pandas as pd


class QuestionFeatureExtractor:
    """
    Extract Question-Level (Q) timing features from a single-interview CIR frame.
    """

    def extract(self, cir_df: pd.DataFrame) -> pd.DataFrame:
        """
        Parameters:
            cir_df: CIR standardized dataframe for a single interview.

        Returns:
            DataFrame indexed by field_name with columns Q-01 to Q-10.
        """
        q_features = []

        # Only process rows that correspond to actual question or field
        # interactions. Administrative events are excluded.
        valid_cir = cir_df[
            (~cir_df["field_name"].isin(["unknown_field", "MainSection"]))
            & (~cir_df["event_type"].isin(["form_start", "form_end"]))
        ].copy()

        if valid_cir.empty:
            return pd.DataFrame()

        # Pre-compute revisit flags at the interview level so revisit_count is
        # based on leaving and returning to a field, rather than repeated edits
        # within one continuous visit.
        sorted_cir = valid_cir.sort_values("start_ms")
        field_sequence = sorted_cir["field_name"].tolist()
        revisit_set = set()
        revisit_counts = {}
        seen_fields = set()
        prev_field = None
        for field_name in field_sequence:
            if field_name != prev_field:
                if field_name in seen_fields:
                    revisit_set.add(field_name)
                    revisit_counts[field_name] = revisit_counts.get(field_name, 0) + 1
                seen_fields.add(field_name)
                prev_field = field_name

        groups = valid_cir.groupby("field_name")

        for field, group in groups:
            group = group.sort_values("start_ms")

            # Exclude navigation events from the response-time window so back or
            # jump markers do not inflate time-on-question calculations.
            nav_mask = group["event_type"].str.contains(
                "jump|back|backward|forward|skip", case=False, na=False
            )
            question_events = group[~nav_mask]
            if not question_events.empty:
                end_max = question_events["end_ms"].max()
                start_min = question_events["start_ms"].min()
                f2l = end_max - start_min if pd.notna(end_max) and pd.notna(start_min) else 0
            elif len(group) >= 1:
                # All events are navigation, so use the full window as a fallback.
                end_max = group["end_ms"].max()
                start_min = group["start_ms"].min()
                f2l = end_max - start_min if pd.notna(end_max) and pd.notna(start_min) else 0
            else:
                f2l = 0

            # Q-01 is the total time actively spent on the field: the sum of
            # event durations, excluding navigation markers. Q-10 is the
            # first-to-last window, which additionally spans internal gaps.
            if not question_events.empty:
                rt_ms = question_events["duration_ms"].fillna(0).clip(lower=0).sum()
            elif len(group) >= 1:
                rt_ms = group["duration_ms"].fillna(0).clip(lower=0).sum()
            else:
                rt_ms = 0

            # Q-02 time_to_first_interaction
            # Use field/question start and end markers when available, otherwise
            # fall back to the duration of the first recorded event.
            start_events = group[group["event_type"].isin(["field_start", "question-start"])]
            end_events = group[group["event_type"].isin(["field_end", "question-end"])]
            if not start_events.empty and not end_events.empty:
                ttfi = end_events["start_ms"].iloc[0] - start_events["start_ms"].iloc[0]
                ttfi = max(0, ttfi)
            else:
                ttfi = group["duration_ms"].iloc[0] if not group.empty else 0

            # Multiple consecutive events on a field indicate edits during the
            # same visit.
            edit_count = max(0, len(group) - 1)

            # Q-04 revisit_flag: field was returned to after leaving.
            revisit_flag = 1 if field in revisit_set else 0

            revisit_count = revisit_counts.get(field, 0)
            fcr = 1.0 if rt_ms > 0 else 0.0

            idle_time = 0
            if len(group) > 1:
                gaps = group["start_ms"].values[1:] - group["end_ms"].values[:-1]
                idle_time = gaps[gaps > 0].sum()

            keystroke_count = len(group)

            # Q-09 constraint_trigger_count
            ctc = len(
                group[group["event_type"].str.contains("error|constraint|invalid", case=False, na=False)]
            )

            q_features.append(
                {
                    "field_name": field,
                    "Q-01_response_time_ms": rt_ms,
                    "Q-02_time_to_first_interaction": ttfi,
                    "Q-03_edit_count": edit_count,
                    "Q-04_revisit_flag": revisit_flag,
                    "Q-05_revisit_count": revisit_count,
                    "Q-06_field_completion_ratio": fcr,
                    "Q-07_idle_time_ms": idle_time,
                    "Q-08_keystroke_count": keystroke_count,
                    "Q-09_constraint_trigger_count": ctc,
                    "Q-10_first_to_last_interaction_duration": f2l,
                }
            )

        return pd.DataFrame(q_features).set_index("field_name")
