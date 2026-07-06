import numpy as np
import pandas as pd


class SectionFeatureExtractor:
    """
    Extract Section-Level (S) timing features from the structured CIR dataframe.
    """

    @staticmethod
    def _infer_section_name(field_name) -> str:
        """
        Infer a stable section label from either XPath-like nodes or flat names.
        """
        name = str(field_name).strip()
        if not name or name == "unknown_field":
            return "MainSection"

        path_parts = [part for part in name.split("/") if part]
        if path_parts:
            if path_parts[0].lower() == "data":
                if len(path_parts) >= 3:
                    return path_parts[1]
                if len(path_parts) == 2:
                    return "MainSection"
            return path_parts[-1].split("_")[0] if "_" in path_parts[-1] else "MainSection"

        leaf_name = name.rsplit("/", 1)[-1]
        if "_" in leaf_name:
            return leaf_name.split("_", 1)[0]
        return "MainSection"

    def extract(self, cir_df: pd.DataFrame, q_features_df: pd.DataFrame) -> pd.DataFrame:
        if cir_df.empty:
            return pd.DataFrame()

        # Administrative form-level events (form start/end rows with blank
        # nodes) are not part of any questionnaire section; keeping them
        # would create a pseudo-section whose gaps span the whole interview.
        cir_df = cir_df[~cir_df["event_type"].isin(["form_start", "form_end"])].copy()
        if cir_df.empty:
            return pd.DataFrame()

        cir_df = cir_df.assign(section_name=cir_df["field_name"].apply(self._infer_section_name))

        section_field_counts = {}
        for section_name, section_group in cir_df.groupby("section_name"):
            section_field_counts[section_name] = section_group["field_name"].nunique()
        max_fields_any_section = max(section_field_counts.values()) if section_field_counts else 1

        s_features = []
        groups = cir_df.groupby("section_name")

        for section, group in groups:
            group = group.sort_values("start_ms")

            section_questions = group["field_name"].unique()
            if q_features_df.empty:
                q_sub = pd.DataFrame()
            else:
                q_sub = q_features_df[q_features_df.index.isin(section_questions)]

            pace = q_sub["Q-01_response_time_ms"].mean() if not q_sub.empty else 0

            end_max = group["end_ms"].max()
            start_min = group["start_ms"].min()
            duration = end_max - start_min if pd.notna(end_max) and pd.notna(start_min) else 0

            variance = q_sub["Q-01_response_time_ms"].var() if len(q_sub) > 1 else 0

            pauses = np.array([])
            if len(group) > 1:
                gaps = group["start_ms"].values[1:] - group["end_ms"].values[:-1]
                pauses = gaps[gaps > 0]

            p_5s = len(pauses[pauses > 5000]) if len(pauses) > 0 else 0
            p_30s = len(pauses[pauses > 30000]) if len(pauses) > 0 else 0
            mean_p = pauses.mean() if len(pauses) > 0 else 0
            max_p = pauses.max() if len(pauses) > 0 else 0

            back_nav = len(group[group["event_type"].str.contains("back|backward", case=False, na=False)])

            # Since no questionnaire schema is available at runtime, completion is
            # approximated relative to the most-complete section observed in the
            # current interview dataset.
            fields_visited = group["field_name"].nunique()
            denom = max(max_fields_any_section, 1)
            comp_rate = min(1.0, fields_visited / denom)

            s_features.append(
                {
                    "section_name": section,
                    "S-01_mean_section_pace": pace,
                    "S-02_section_duration_ms": duration,
                    "S-03_within_section_variance": variance,
                    "S-05_pause_count_5s": p_5s,
                    "S-06_pause_count_30s": p_30s,
                    "S-07_mean_pause_duration_ms": mean_p,
                    "S-08_max_pause_duration_ms": max_p,
                    "S-09_back_nav_count_section": back_nav,
                    "S-10_section_completion_rate": comp_rate,
                }
            )

        df_sec = pd.DataFrame(s_features).set_index("section_name")

        if not df_sec.empty:
            global_pace = q_features_df["Q-01_response_time_ms"].mean() if not q_features_df.empty else 1.0
            global_pace = global_pace if global_pace > 0 else 1.0
            df_sec = df_sec.assign(
                **{"S-04_section_to_section_pace_ratio": df_sec["S-01_mean_section_pace"] / global_pace}
            )

        return df_sec
