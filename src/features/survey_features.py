import numpy as np
import pandas as pd


class SurveyFeatureExtractor:
    """
    Extract Survey-Level (V) timing features from the structured CIR dataframe.
    """

    @staticmethod
    def _timestamp_from_ms(value) -> pd.Timestamp | None:
        """
        Safely convert an epoch-millisecond scalar into a pandas Timestamp.
        """
        if pd.isna(value):
            return None

        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None

        if not np.isfinite(numeric):
            return None

        try:
            return pd.Timestamp(int(round(numeric)), unit="ms", tz="UTC")
        except (TypeError, ValueError, OverflowError):
            return None

    def extract(self, cir_df: pd.DataFrame) -> dict:
        if cir_df.empty:
            return {}

        df = cir_df.sort_values("start_ms").copy()
        features = {}

        if len(df) > 0:
            features["V-01_total_interview_duration_ms"] = df["end_ms"].max() - df["start_ms"].min()
        else:
            features["V-01_total_interview_duration_ms"] = 0

        n_events = len(df)
        if n_events >= 3:

            def calc_slice_speed(slice_df):
                n_fields = len(slice_df[slice_df["event_type"] == "field_end"])
                if n_fields > 0:
                    delta = slice_df["end_ms"].max() - slice_df["start_ms"].min()
                    return delta / n_fields
                return slice_df["duration_ms"].mean() if not slice_df["duration_ms"].isna().all() else 0.0

            third = max(1, n_events // 3)
            early = df.iloc[:third]
            late = df.iloc[-third:]

            features["V-02_speed_trajectory_early"] = calc_slice_speed(early)
            features["V-03_speed_trajectory_late"] = calc_slice_speed(late)

            # Guard against divide-by-zero for degenerate early slices.
            if features["V-02_speed_trajectory_early"] > 0:
                features["V-04_speed_trajectory_ratio"] = (
                    features["V-03_speed_trajectory_late"] / features["V-02_speed_trajectory_early"]
                )
            else:
                features["V-04_speed_trajectory_ratio"] = None
        else:
            features["V-02_speed_trajectory_early"] = None
            features["V-03_speed_trajectory_late"] = None
            features["V-04_speed_trajectory_ratio"] = None

        back_mask = df["event_type"].str.contains("back|backward|jump", case=False, na=False)
        backs = int(back_mask.sum())
        features["V-06_back_navigation_total_count"] = backs
        n_question_events = len(df[~back_mask])
        features["V-05_back_navigation_rate"] = backs / n_question_events if n_question_events > 0 else 0

        first_ms = df["start_ms"].min()
        dt = self._timestamp_from_ms(first_ms)
        if dt is not None:
            features["V-07_time_of_day_hour"] = dt.hour
            features["V-08_day_of_week"] = dt.dayofweek
        else:
            features["V-07_time_of_day_hour"] = np.nan
            features["V-08_day_of_week"] = np.nan

        features["V-09_session_length_vs_median"] = np.nan

        # Track the longest uninterrupted sequence without back-navigation.
        max_consecutive = 0
        current_run = 0
        for evt in df["event_type"]:
            if str(evt).lower() not in ("back", "backward", "jump"):
                current_run += 1
                max_consecutive = max(max_consecutive, current_run)
            else:
                current_run = 0
        features["V-10_zero_back_nav_flag"] = 1 if max_consecutive >= 20 else 0

        return features
