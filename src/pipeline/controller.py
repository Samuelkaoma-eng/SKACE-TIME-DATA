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

class PipelineController:
    """
    Orchestrates the paradata feature extraction pipeline.
    Ensures low coupling by passing only DataFrames between components.
    """
    
    def __init__(self, parser_type: str = 'surveycto'):
        if parser_type.lower() == 'surveycto':
            self.parser = SurveyCTOParser()
        elif parser_type.lower() == 'odk':
            self.parser = ODKParser()
        else:
            raise ValueError(f"Unknown parser type: {parser_type}")
            
        self.q_extractor = QuestionFeatureExtractor()
        self.s_extractor = SectionFeatureExtractor()
        self.v_extractor = SurveyFeatureExtractor()
        self.t_extractor = StatisticalFeatureExtractor()
        self.anomaly_detector = AnomalyDetector()
        
    def process_file(self, filepath: Union[str, Path]) -> List[dict]:
        """
        Processes a single paradata CSV log. 
        Returns a list of dictionaries, one per interview in the log.
        """
        filepath = Path(filepath)
        print(f"  -> Parsing {filepath.name} using {type(self.parser).__name__}...")
        
        try:
            # Parse into CIR
            cir_df = self.parser.parse(filepath)
        except Exception as e:
            print(f"  [ERROR] Parsing failed for {filepath.name}: {e}")
            return []
            
        if cir_df.empty:
            print(f"  [WARN] {filepath.name} produced an empty abstract DataFrame.")
            return []
            
        # Group by interview_id
        features_list = []
        groups = cir_df.groupby('interview_id')
        
        for interview_id, group_df in groups:
            try:
                # 1. Question level
                q_df = self.q_extractor.extract(group_df)
                
                # 2. Section level
                s_df = self.s_extractor.extract(group_df, q_df)
                
                # 3. Survey level
                v_dict = self.v_extractor.extract(group_df)
                
                # 4. Statistical level (built from Question level)
                t_dict = self.t_extractor.extract(q_df)
                
                # Combine all features into a single row summary for this interview
                final_row = {'file_name': filepath.name, 'interview_id': interview_id}
                
                # Aggregate Q and S features slightly or just keep them as JSON strings?
                # The user expects a single row summary. We will take the mean of 
                # Q and S features across the interview to make it flat.
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
                    if q_sum > v_total + 1000: # 1s buffer for floating point/rounding
                        final_row['is_data_quality_issue'] = 1
                    
                features_list.append(final_row)
            except Exception as e:
                 print(f"  [ERROR] Feature extraction failed for interview {interview_id}: {e}")
                 
        return features_list
        
    def process_batch(self, filepaths: List[Union[str, Path]]) -> pd.DataFrame:
        """
        Process multiple files and apply global evaluations (like relative speed).
        """
        all_features = []
        for fp in filepaths:
            all_features.extend(self.process_file(fp))
            
        if not all_features:
            return pd.DataFrame()
            
        df = pd.DataFrame(all_features)
        
        # Apply global survey-level logic (V-09 session_length_vs_median)
        if 'V-01_total_interview_duration_ms' in df.columns:
            median_dur = df['V-01_total_interview_duration_ms'].median()
            if np.isnan(median_dur) or median_dur == 0:
                df['V-09_session_length_vs_median'] = 1.0
            else:
                df['V-09_session_length_vs_median'] = df['V-01_total_interview_duration_ms'] / median_dur
                
        # Apply Anomaly Detection
        df = self.anomaly_detector.detect(df)
        
        return df
