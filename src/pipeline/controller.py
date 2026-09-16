import pandas as pd
import numpy as np
from pathlib import Path
from typing import Union, List

from src.parsers.surveycto_parser import SurveyCTOParser
from src.parsers.odk_parser import ODKParser
from src.features.question_features import QuestionFeatureExtractor
from src.features.section_features import SectionFeatureExtractor
from src.features.survey_features import SurveyFeatureExtractor
from src.features.statistical_features import StatisticalFeatureExtractor
from src.validation.anomaly_detector import AnomalyDetector
from src.validation.detector_config import validate_detector_config

ODK_NATIVE_EVENTS = {
    'form start',
    'end screen',
    'group questions',
    'form save',
    'form exit',
    'form resume',
    'form finalize',
}


class PipelineController:
    """
    Orchestrates the paradata feature extraction pipeline.
    Ensures low coupling by passing only DataFrames between components.
    """
    
    def __init__(self, parser_type: str = 'auto', detector_config: dict | None = None):
        self.parser_type = parser_type.lower()
        if self.parser_type not in ['auto', 'surveycto', 'odk']:
            raise ValueError(f"Unknown parser type: {parser_type}")
            
        self.q_extractor = QuestionFeatureExtractor()
        self.s_extractor = SectionFeatureExtractor()
        self.v_extractor = SurveyFeatureExtractor()
        self.t_extractor = StatisticalFeatureExtractor()
        self.detector_config = validate_detector_config(detector_config or {})
        self.anomaly_detector = AnomalyDetector(**self.detector_config)

    @staticmethod
    def _looks_like_iso_timestamp(df_raw: pd.DataFrame) -> bool:
        """
        Heuristic used by auto-detection for ODK-like logs that do not expose
        `instance_id` or `name` but do store timestamps as ISO 8601 strings.
        """
        for candidate in ["start", "start_time", "ts_start", "end", "end_time", "ts_end"]:
            if candidate not in df_raw.columns:
                continue
            sample = df_raw[candidate].dropna().astype(str).head(20)
            if sample.empty:
                continue
            numeric_ratio = pd.to_numeric(sample, errors="coerce").notna().mean()
            if numeric_ratio < 0.5:
                return True
        return False

    def _parse_to_cir(self, filepath: Path) -> pd.DataFrame:
        """
        Parse a raw audit log into the Common Intermediate Representation (CIR).
        """
        if self.parser_type == 'auto':
            try:
                # Content-based auto-detection.
                df_raw = pd.read_csv(filepath, comment='#', low_memory=False)
                cols = set(str(c).lower().strip() for c in df_raw.columns)

                # Mixed-format files can contain both structural identifiers.
                if 'instance_id' in cols and ('interview_id' in cols or 'uuid' in cols):
                    print(f"  -> Hybrid format detected in {filepath.name}. Splitting dataset...")

                    # Drop repeated header rows that sometimes appear mid-file.
                    df_raw = df_raw[df_raw['instance_id'] != 'instance_id']

                    odk_raw = df_raw[df_raw['instance_id'].notna()].copy()
                    scto_raw = df_raw[df_raw['instance_id'].isna()].copy()

                    cir_dfs = []
                    import os, tempfile

                    # Drop empty columns so each parser sees only its relevant schema.
                    if not odk_raw.empty:
                        odk_clean = odk_raw.dropna(axis=1, how='all')
                        tmp_odk = tempfile.NamedTemporaryFile(
                            mode='w', suffix='.csv', delete=False, encoding='utf-8'
                        )
                        try:
                            odk_clean.to_csv(tmp_odk.name, index=False)
                            tmp_odk.close()
                            cir_dfs.append(ODKParser().parse(tmp_odk.name))
                        finally:
                            if os.path.exists(tmp_odk.name):
                                os.remove(tmp_odk.name)

                    if not scto_raw.empty:
                        scto_clean = scto_raw.dropna(axis=1, how='all')
                        tmp_scto = tempfile.NamedTemporaryFile(
                            mode='w', suffix='.csv', delete=False, encoding='utf-8'
                        )
                        try:
                            scto_clean.to_csv(tmp_scto.name, index=False)
                            tmp_scto.close()
                            cir_dfs.append(SurveyCTOParser().parse(tmp_scto.name))
                        finally:
                            if os.path.exists(tmp_scto.name):
                                os.remove(tmp_scto.name)

                    return pd.concat(cir_dfs, ignore_index=True) if cir_dfs else pd.DataFrame()

                if 'instance_id' in cols or 'name' in cols:
                    print(f"  -> Parsing {filepath.name} using ODKParser...")
                    return ODKParser().parse(filepath)

                # A native ODK audit log has node/start/end columns like a
                # SurveyCTO export, so it is identified by its event
                # vocabulary instead. These names appear in ODK's documented
                # audit log and in no SurveyCTO export.
                if 'event' in df_raw.columns:
                    events = set(df_raw['event'].astype(str).str.strip().str.lower())
                    if events & ODK_NATIVE_EVENTS:
                        print(f"  -> Parsing {filepath.name} using ODKParser (native audit log)...")
                        return ODKParser().parse(filepath)

                if self._looks_like_iso_timestamp(df_raw):
                    print(f"  -> Parsing {filepath.name} using ODKParser...")
                    return ODKParser().parse(filepath)

                print(f"  -> Parsing {filepath.name} using SurveyCTOParser...")
                return SurveyCTOParser().parse(filepath)

            except Exception as e:
                print(f"  [ERROR] Auto-detection failed for {filepath.name}: {e}")
                return pd.DataFrame()

        if self.parser_type == 'odk':
            print(f"  -> Parsing {filepath.name} using ODKParser...")
            return ODKParser().parse(filepath)

        print(f"  -> Parsing {filepath.name} using SurveyCTOParser...")
        return SurveyCTOParser().parse(filepath)

    @staticmethod
    def _with_interview_context(
        features_df: pd.DataFrame,
        filepath_name: str,
        interview_id: str,
        entity_label: str,
    ) -> pd.DataFrame:
        """
        Convert a feature table indexed by field/section into an export-ready table.
        """
        if features_df.empty:
            return pd.DataFrame(columns=['file_name', 'interview_id', entity_label])

        export_df = features_df.reset_index()
        export_df.insert(0, 'interview_id', interview_id)
        export_df.insert(0, 'file_name', filepath_name)
        return export_df

    def _extract_interview_outputs(self, filepath_name: str, interview_id: str, group_df: pd.DataFrame) -> dict:
        """
        Build all per-interview artifacts needed by the pipeline.
        """
        # 1. Question level
        q_df = self.q_extractor.extract(group_df)

        # 2. Section level
        s_df = self.s_extractor.extract(group_df, q_df)

        # 3. Survey level
        v_dict = self.v_extractor.extract(group_df)

        # 4. Statistical level (built from Question level)
        t_dict = self.t_extractor.extract(q_df)

        # Combine all features into a single row summary for this interview
        final_row = {'file_name': filepath_name, 'interview_id': interview_id}

        # Aggregate Q and S features to preserve the current flat interview-level output.
        if not s_df.empty:
            s_summary = s_df.mean(numeric_only=True).to_dict()
        else:
            s_summary = {}

        final_row.update(v_dict)
        final_row.update(t_dict)
        final_row.update(s_summary)

        if not q_df.empty:
            q_summary = q_df.mean(numeric_only=True).to_dict()
            final_row.update(q_summary)

            # Hierarchical Integrity Check
            # sum(rt_ms) should be <= total_duration
            q_sum = q_df['Q-01_response_time_ms'].sum()
            v_total = v_dict.get('V-01_total_interview_duration_ms', 0)
            if q_sum > v_total + 1000:  # 1s buffer for floating point/rounding
                final_row['is_data_quality_issue'] = 1

        question_features = self._with_interview_context(q_df, filepath_name, interview_id, 'field_name')
        section_features = self._with_interview_context(s_df, filepath_name, interview_id, 'section_name')

        return {
            'interview_features': final_row,
            'question_features': question_features,
            'section_features': section_features,
        }

    def process_file_detailed(self, filepath: Union[str, Path]) -> dict:
        """
        Process a single paradata CSV log and retain the granular feature tables.

        Returns
        -------
        dict
            {
                "interview_features": List[dict],
                "question_features": pd.DataFrame,
                "section_features": pd.DataFrame,
            }
        """
        filepath = Path(filepath)
        cir_df = self._parse_to_cir(filepath)

        if cir_df.empty:
            print(f"  [WARN] {filepath.name} produced an empty abstract DataFrame.")
            return {
                'interview_features': [],
                'question_features': pd.DataFrame(columns=['file_name', 'interview_id', 'field_name']),
                'section_features': pd.DataFrame(columns=['file_name', 'interview_id', 'section_name']),
            }

        interview_features = []
        question_frames = []
        section_frames = []

        groups = cir_df.groupby('interview_id')

        for interview_id, group_df in groups:
            try:
                outputs = self._extract_interview_outputs(filepath.name, interview_id, group_df)
                interview_features.append(outputs['interview_features'])

                if not outputs['question_features'].empty:
                    question_frames.append(outputs['question_features'])

                if not outputs['section_features'].empty:
                    section_frames.append(outputs['section_features'])
            except Exception as e:
                print(f"  [ERROR] Feature extraction failed for interview {interview_id}: {e}")

        question_features = (
            pd.concat(question_frames, ignore_index=True)
            if question_frames
            else pd.DataFrame(columns=['file_name', 'interview_id', 'field_name'])
        )
        section_features = (
            pd.concat(section_frames, ignore_index=True)
            if section_frames
            else pd.DataFrame(columns=['file_name', 'interview_id', 'section_name'])
        )

        return {
            'interview_features': interview_features,
            'question_features': question_features,
            'section_features': section_features,
        }
        
    def process_file(self, filepath: Union[str, Path]) -> List[dict]:
        """
        Processes a single paradata CSV log. 
        Returns a list of dictionaries, one per interview in the log.
        """
        detailed = self.process_file_detailed(filepath)
        return detailed['interview_features']

    def process_batch_detailed(self, filepaths: List[Union[str, Path]]) -> dict:
        """
        Process multiple files and retain interview-, question-, and section-level outputs.
        """
        all_features = []
        question_frames = []
        section_frames = []

        for fp in filepaths:
            detailed = self.process_file_detailed(fp)
            all_features.extend(detailed['interview_features'])

            if not detailed['question_features'].empty:
                question_frames.append(detailed['question_features'])

            if not detailed['section_features'].empty:
                section_frames.append(detailed['section_features'])

        if not all_features:
            empty_interview = pd.DataFrame()
            return {
                'interview_features': empty_interview,
                'question_features': pd.DataFrame(columns=['file_name', 'interview_id', 'field_name']),
                'section_features': pd.DataFrame(columns=['file_name', 'interview_id', 'section_name']),
            }

        interview_df = pd.DataFrame(all_features)

        # Apply global survey-level logic (V-09 session_length_vs_median)
        if 'V-01_total_interview_duration_ms' in interview_df.columns:
            median_dur = interview_df['V-01_total_interview_duration_ms'].median()
            if np.isnan(median_dur) or median_dur == 0:
                interview_df.loc[:, 'V-09_session_length_vs_median'] = 1.0
            else:
                interview_df.loc[:, 'V-09_session_length_vs_median'] = (
                    interview_df['V-01_total_interview_duration_ms'] / median_dur
                )

        # Apply Anomaly Detection
        interview_df = self.anomaly_detector.detect(interview_df)

        question_features = (
            pd.concat(question_frames, ignore_index=True)
            if question_frames
            else pd.DataFrame(columns=['file_name', 'interview_id', 'field_name'])
        )
        section_features = (
            pd.concat(section_frames, ignore_index=True)
            if section_frames
            else pd.DataFrame(columns=['file_name', 'interview_id', 'section_name'])
        )

        return {
            'interview_features': interview_df,
            'question_features': question_features,
            'section_features': section_features,
        }
        
    def process_batch(self, filepaths: List[Union[str, Path]]) -> pd.DataFrame:
        """
        Process multiple files and apply global evaluations (like relative speed).
        """
        detailed = self.process_batch_detailed(filepaths)
        return detailed['interview_features']
