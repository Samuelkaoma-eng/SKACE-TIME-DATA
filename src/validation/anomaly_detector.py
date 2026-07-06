import numpy as np
import pandas as pd


class AnomalyDetector:
    """
    Apply transparent, rule-based anomaly detection to interview-level features.

    The score is the count of active scored flags for each interview. This keeps
    the anomaly report reproducible from the feature dataset without relying on
    hidden model state or learned weights.
    """

    IQR_MULTIPLIER = 1.5
    IQR_FLAG_COLUMNS = [
        "flag_iqr_duration",
        "flag_iqr_rt_mean",
        "flag_iqr_entropy",
        "flag_iqr_variance",
    ]
    RULE_FLAG_COLUMNS = [
        "flag_too_fast",
        "flag_too_slow",
        "flag_short_relative_duration",
        "flag_low_mean_rt",
        "flag_zero_back_nav",
        "flag_low_entropy",
        "flag_uniform_timing",
        "flag_low_rt_iqr",
        "flag_low_section_variance",
        "flag_high_back_nav",
        "flag_moderate_back_nav",
        "flag_long_pause_relative",
        "flag_elevated_pause",
        "flag_rule_pause",
    ]
    DATA_QUALITY_FLAG_COLUMNS = [
        "flag_invalid_ratio",
        "flag_missing_data",
        "flag_inconsistent_metrics",
    ]
    SCORED_FLAG_COLUMNS = [
        "flag_too_fast",
        "flag_too_slow",
        "flag_short_relative_duration",
        "flag_low_mean_rt",
        "flag_low_entropy",
        "flag_uniform_timing",
        "flag_low_rt_iqr",
        "flag_low_section_variance",
        "flag_high_back_nav",
        "flag_moderate_back_nav",
        "flag_long_pause_relative",
        "flag_elevated_pause",
        "flag_zero_back_nav",
        "flag_rule_pause",
        "flag_invalid_ratio",
    ]

    def __init__(
        self,
        uniform_timing_cv=0.1,
        behavior_score_threshold=2,
        anomalous_score_threshold=5,
        too_fast_ms=6000,
        too_slow_ms=3600000,
        low_entropy_threshold=0.5,
        low_variance_threshold=10,
        short_session_median_ratio=0.5,
        low_mean_rt_median_ratio=0.5,
        low_rt_iqr_median_ratio=0.5,
        low_section_variance_median_ratio=0.25,
        moderate_back_nav_rate_threshold=0.25,
        long_pause_median_ratio=2.0,
        high_back_nav_rate_threshold=0.5,
        rule_pause_count_min=2,
        rule_pause_min_ms=280000,
        elevated_pause_median_ratio=2.5,
    ):
        self.uniform_timing_cv = uniform_timing_cv
        self.behavior_score_threshold = behavior_score_threshold
        self.anomalous_score_threshold = anomalous_score_threshold
        self.too_fast_ms = too_fast_ms
        self.too_slow_ms = too_slow_ms
        self.low_entropy_threshold = low_entropy_threshold
        self.low_variance_threshold = low_variance_threshold
        self.short_session_median_ratio = short_session_median_ratio
        self.low_mean_rt_median_ratio = low_mean_rt_median_ratio
        self.low_rt_iqr_median_ratio = low_rt_iqr_median_ratio
        self.low_section_variance_median_ratio = low_section_variance_median_ratio
        self.moderate_back_nav_rate_threshold = moderate_back_nav_rate_threshold
        self.long_pause_median_ratio = long_pause_median_ratio
        self.high_back_nav_rate_threshold = high_back_nav_rate_threshold
        self.rule_pause_count_min = rule_pause_count_min
        self.rule_pause_min_ms = rule_pause_min_ms
        self.elevated_pause_median_ratio = elevated_pause_median_ratio

    @staticmethod
    def _iqr_flag(series: pd.Series, multiplier: float = 1.5) -> pd.Series:
        """Flag values outside Tukey IQR fences."""
        values = pd.to_numeric(series, errors="coerce")
        q1 = values.quantile(0.25)
        q3 = values.quantile(0.75)
        iqr = q3 - q1
        if pd.isna(iqr) or iqr <= 0:
            return pd.Series(0, index=series.index, dtype="Int64")
        lower = q1 - multiplier * iqr
        upper = q3 + multiplier * iqr
        return ((values < lower) | (values > upper)).astype("Int64")

    @staticmethod
    def _positive_median(series: pd.Series) -> float | None:
        values = pd.to_numeric(series, errors="coerce")
        values = values[values > 0]
        if values.empty:
            return None
        median = float(values.median())
        return median if np.isfinite(median) and median > 0 else None

    @classmethod
    def reconstruct_score(cls, row: pd.Series) -> int:
        iqr_score = min(sum(int(row.get(column, 0)) for column in cls.IQR_FLAG_COLUMNS), 1)
        rule_score = sum(int(row.get(column, 0)) for column in cls.SCORED_FLAG_COLUMNS)
        return int(iqr_score + rule_score)

    def _initialize_flags(self, df: pd.DataFrame) -> list[str]:
        flag_columns = (
            self.DATA_QUALITY_FLAG_COLUMNS
            + self.RULE_FLAG_COLUMNS
            + self.IQR_FLAG_COLUMNS
        )
        for column in flag_columns:
            df[column] = 0
        return flag_columns

    def _apply_data_quality_flags(self, df: pd.DataFrame) -> None:
        if "V-04_speed_trajectory_ratio" in df.columns:
            df.loc[df["V-04_speed_trajectory_ratio"].isna(), "flag_invalid_ratio"] = 1

        if "T-06_rt_mean" in df.columns:
            df.loc[
                (df["T-06_rt_mean"].isna()) | (df["T-06_rt_mean"] == 0),
                "flag_missing_data",
            ] = 1

        if "V-07_time_of_day_hour" in df.columns:
            df.loc[df["V-07_time_of_day_hour"] < 0, "flag_inconsistent_metrics"] = 1

        if "V-01_total_interview_duration_ms" in df.columns:
            df.loc[df["V-01_total_interview_duration_ms"] < 0, "flag_inconsistent_metrics"] = 1

        if all(c in df.columns for c in ["T-10_rt_max", "T-09_rt_min"]):
            df.loc[df["T-10_rt_max"] < df["T-09_rt_min"], "flag_inconsistent_metrics"] = 1

        if all(c in df.columns for c in ["S-02_section_duration_ms", "Q-01_response_time_ms"]):
            df.loc[
                df["S-02_section_duration_ms"] < df["Q-01_response_time_ms"],
                "flag_inconsistent_metrics",
            ] = 1

        if all(c in df.columns for c in ["Q-07_idle_time_ms", "V-01_total_interview_duration_ms"]):
            df.loc[
                df["Q-07_idle_time_ms"] > df["V-01_total_interview_duration_ms"],
                "flag_inconsistent_metrics",
            ] = 1

    def _apply_rule_flags(self, df: pd.DataFrame) -> None:
        if "V-01_total_interview_duration_ms" in df.columns:
            duration = df["V-01_total_interview_duration_ms"]
            df.loc[duration < self.too_fast_ms, "flag_too_fast"] = 1
            df.loc[duration > self.too_slow_ms, "flag_too_slow"] = 1

        if "V-09_session_length_vs_median" in df.columns:
            df.loc[
                df["V-09_session_length_vs_median"] < self.short_session_median_ratio,
                "flag_short_relative_duration",
            ] = 1

        if "T-06_rt_mean" in df.columns:
            mean_rt_median = self._positive_median(df["T-06_rt_mean"])
            if mean_rt_median is not None:
                threshold = mean_rt_median * self.low_mean_rt_median_ratio
                df.loc[df["T-06_rt_mean"] < threshold, "flag_low_mean_rt"] = 1

        if "T-03_rt_entropy" in df.columns:
            df.loc[df["T-03_rt_entropy"] < self.low_entropy_threshold, "flag_low_entropy"] = 1

        if "T-01_rt_variance" in df.columns:
            df.loc[df["T-01_rt_variance"] < self.low_variance_threshold, "flag_uniform_timing"] = 1
        if "T-08_rt_cv" in df.columns:
            df.loc[df["T-08_rt_cv"] < self.uniform_timing_cv, "flag_uniform_timing"] = 1

        if "T-02_rt_iqr" in df.columns:
            rt_iqr_median = self._positive_median(df["T-02_rt_iqr"])
            if rt_iqr_median is not None:
                threshold = rt_iqr_median * self.low_rt_iqr_median_ratio
                compressed_context = (
                    (df["flag_low_entropy"] == 1)
                    | (df["flag_uniform_timing"] == 1)
                )
                df.loc[
                    (df["T-02_rt_iqr"] <= threshold) & compressed_context,
                    "flag_low_rt_iqr",
                ] = 1

        if "S-03_within_section_variance" in df.columns:
            section_var_median = self._positive_median(df["S-03_within_section_variance"])
            if section_var_median is not None:
                threshold = section_var_median * self.low_section_variance_median_ratio
                compressed_context = (
                    (df["flag_low_entropy"] == 1)
                    | (df["flag_uniform_timing"] == 1)
                    | (df["flag_low_rt_iqr"] == 1)
                )
                df.loc[
                    (df["S-03_within_section_variance"] <= threshold) & compressed_context,
                    "flag_low_section_variance",
                ] = 1

        zero_back_source = pd.Series(False, index=df.index)
        if "V-10_zero_back_nav_flag" in df.columns:
            zero_back_source = zero_back_source | (df["V-10_zero_back_nav_flag"] == 1)
        if "V-06_back_navigation_total_count" in df.columns:
            zero_back_source = zero_back_source | (df["V-06_back_navigation_total_count"] == 0)
        compressed_context = (
            (df["flag_low_entropy"] == 1)
            | (df["flag_uniform_timing"] == 1)
            | (df["flag_low_rt_iqr"] == 1)
            | (df["flag_low_section_variance"] == 1)
        )
        df.loc[zero_back_source & compressed_context, "flag_zero_back_nav"] = 1

        if "V-05_back_navigation_rate" in df.columns:
            df.loc[
                df["V-05_back_navigation_rate"] >= self.high_back_nav_rate_threshold,
                "flag_high_back_nav",
            ] = 1
            df.loc[
                df["V-05_back_navigation_rate"] >= self.moderate_back_nav_rate_threshold,
                "flag_moderate_back_nav",
            ] = 1

        if "S-08_max_pause_duration_ms" in df.columns:
            max_pause_median = self._positive_median(df["S-08_max_pause_duration_ms"])
            if max_pause_median is not None:
                threshold = max_pause_median * self.long_pause_median_ratio
                df.loc[
                    df["S-08_max_pause_duration_ms"] >= threshold,
                    "flag_long_pause_relative",
                ] = 1
        # Disengagement marker: mean inter-question pause well above the
        # sample median. Median-relative, so the threshold adapts to the
        # instrument rather than assuming absolute pause lengths
        # [Conrad et al. 3].
        if "S-07_mean_pause_duration_ms" in df.columns:
            mean_pause_median = self._positive_median(df["S-07_mean_pause_duration_ms"])
            if mean_pause_median is not None:
                threshold = mean_pause_median * self.elevated_pause_median_ratio
                df.loc[
                    df["S-07_mean_pause_duration_ms"] >= threshold,
                    "flag_elevated_pause",
                ] = 1

        pause_flag = pd.Series(False, index=df.index)
        if "S-06_pause_count_30s" in df.columns:
            pause_flag = pause_flag | (df["S-06_pause_count_30s"] >= self.rule_pause_count_min)
        if "S-08_max_pause_duration_ms" in df.columns:
            pause_flag = pause_flag & (df["S-08_max_pause_duration_ms"] >= self.rule_pause_min_ms)
        df.loc[pause_flag, "flag_rule_pause"] = 1

    def _apply_iqr_flags(self, df: pd.DataFrame) -> None:
        if len(df) <= 3:
            return

        if "V-01_total_interview_duration_ms" in df.columns:
            df.loc[:, "flag_iqr_duration"] = self._iqr_flag(
                df["V-01_total_interview_duration_ms"], self.IQR_MULTIPLIER
            )

        if "T-06_rt_mean" in df.columns:
            df.loc[:, "flag_iqr_rt_mean"] = self._iqr_flag(
                df["T-06_rt_mean"], self.IQR_MULTIPLIER
            )

        if "T-03_rt_entropy" in df.columns:
            df.loc[:, "flag_iqr_entropy"] = self._iqr_flag(
                df["T-03_rt_entropy"], self.IQR_MULTIPLIER
            )

        if "T-01_rt_variance" in df.columns:
            df.loc[:, "flag_iqr_variance"] = self._iqr_flag(
                df["T-01_rt_variance"], self.IQR_MULTIPLIER
            )

    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Evaluate the combined feature dataset for quality issues and anomalies.
        """
        if df.empty:
            return df

        df = df.copy()
        flag_columns = self._initialize_flags(df)

        self._apply_data_quality_flags(df)
        self._apply_rule_flags(df)
        self._apply_iqr_flags(df)

        dq_trigger = (
            df["flag_missing_data"]
            | df["flag_invalid_ratio"]
            | df["flag_inconsistent_metrics"]
        )
        if "V-01_total_interview_duration_ms" in df.columns:
            dq_trigger = dq_trigger | (df["V-01_total_interview_duration_ms"] <= 0)
        # Preserve integrity flags raised upstream (e.g. the controller's
        # hierarchical check that question time cannot exceed total duration).
        if "is_data_quality_issue" in df.columns:
            dq_trigger = dq_trigger | (
                pd.to_numeric(df["is_data_quality_issue"], errors="coerce").fillna(0).astype(int) == 1
            )
        df.loc[:, "is_data_quality_issue"] = dq_trigger.astype(int)

        iqr_score = sum(
            df[column].fillna(0) for column in self.IQR_FLAG_COLUMNS
        ).clip(upper=1)
        rule_score = sum(
            df[column].fillna(0) for column in self.SCORED_FLAG_COLUMNS
        )
        df.loc[:, "iqr_flags"] = iqr_score.astype("Int64")
        df.loc[:, "rule_flags"] = rule_score.astype("Int64")
        df.loc[:, "anomaly_score"] = (iqr_score + rule_score).astype("Int64")

        def get_category(row):
            if row["is_data_quality_issue"] == 1:
                return "dq_issue"
            if row["anomaly_score"] >= self.anomalous_score_threshold:
                return "anomalous"
            if row["anomaly_score"] >= self.behavior_score_threshold:
                return "suspicious"
            return "normal"

        df.loc[:, "anomaly_category"] = df.apply(get_category, axis=1)
        df.loc[:, "is_anomalous_behavior"] = (
            df["anomaly_score"] >= self.behavior_score_threshold
        ).astype(int)
        df.loc[:, "is_anomalous"] = (
            df["is_anomalous_behavior"] | df["is_data_quality_issue"]
        ).astype(int)

        def join_flags(row):
            active = [column for column in flag_columns if row[column] == 1]
            return ",".join(active)

        df.loc[:, "flagged_features"] = df.apply(join_flags, axis=1)

        def get_status(row):
            if row["is_data_quality_issue"] == 1 or row["anomaly_score"] >= self.anomalous_score_threshold:
                return "FLAGGED"
            if row["anomaly_score"] >= self.behavior_score_threshold:
                return "REVIEW"
            return "CLEAN"

        df.loc[:, "status"] = df.apply(get_status, axis=1)

        for column in flag_columns:
            df.loc[:, column] = df[column].astype("Int64")
        for column in [
            "is_data_quality_issue",
            "is_anomalous_behavior",
            "is_anomalous",
            "anomaly_score",
            "iqr_flags",
            "rule_flags",
        ]:
            df.loc[:, column] = df[column].astype("Int64")

        return df
