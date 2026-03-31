import pandas as pd
import numpy as np
from pathlib import Path
from typing import Union
from .base_parser import BaseParser

class SurveyCTOParser(BaseParser):
    """
    Parser for SurveyCTO audit logs.
    Converts SurveyCTO log structures into the standardized CIR.
    """
    
    def parse(self, filepath: Union[str, Path]) -> pd.DataFrame:
        filepath = Path(filepath)
        try:
            df = pd.read_csv(filepath, comment='#')
            df.dropna(how='all', inplace=True)
        except Exception as e:
            raise ValueError(f"CRITICAL ERROR: Failed to read SurveyCTO CSV file '{filepath}'. Details: {e}")
            
        std_df = pd.DataFrame()
        
        # 1. Interview ID
        if 'interview_id' in df.columns:
            std_df['interview_id'] = df['interview_id']
        elif 'uuid' in df.columns:
             std_df['interview_id'] = df['uuid']
        else:
            std_df['interview_id'] = filepath.stem
            
        # 2. Field Name
        if 'node' in df.columns:
            std_df['field_name'] = df['node'].fillna('unknown_field')
        elif 'question_id' in df.columns:
            std_df['field_name'] = df['question_id'].fillna('unknown_field')
        else:
            std_df['field_name'] = 'unknown_field'
            
        # 3. Event Type
        if 'event' in df.columns:
            std_df['event_type'] = df['event'].fillna('unknown_event').replace({
                'form-start': 'form_start',
                'form-end': 'form_end',
                'question-start': 'field_start',
                'question-end': 'field_end'
            })
        elif 'event_type' in df.columns:
            std_df['event_type'] = df['event_type'].fillna('unknown_event')
        else:
            std_df['event_type'] = 'unknown_event'
            
        # 4. Timing Information
        std_df['start_ms'] = np.nan
        for pt in ['start', 'start_time']:
            if pt in df.columns:
                s_col = pd.to_numeric(df[pt], errors='coerce')
                if s_col.isna().all() and not df[pt].isna().all():
                    # Fallback: parse as ISO datetime. On pandas >= 2.0, this yields datetime64[us], so div 10**3 -> ms.
                    s_col = pd.to_datetime(df[pt], errors='coerce', format='mixed', utc=True).astype('int64') // 10**3
                    s_col.loc[s_col < 0] = np.nan
                else:
                    # Epoch-seconds guard: SurveyCTO canonical format is epoch-ms.
                    # Values < 2e10 are epoch-seconds (before year 2603); multiply by 1000.
                    valid = s_col.dropna()
                    if len(valid) > 0 and valid.median() < 2e10:
                        s_col = s_col * 1000
                std_df['start_ms'] = s_col
                break
            
        std_df['end_ms'] = np.nan
        for pt in ['end', 'end_time']:
            if pt in df.columns:
                e_col = pd.to_numeric(df[pt], errors='coerce')
                if e_col.isna().all() and not df[pt].isna().all():
                    # Fallback: parse as ISO datetime. On pandas >= 2.0, this yields datetime64[us], so div 10**3 -> ms.
                    e_col = pd.to_datetime(df[pt], errors='coerce', format='mixed', utc=True).astype('int64') // 10**3
                    e_col.loc[e_col < 0] = np.nan
                else:
                    # Epoch-seconds guard
                    valid = e_col.dropna()
                    if len(valid) > 0 and valid.median() < 2e10:
                        e_col = e_col * 1000
                std_df['end_ms'] = e_col
                break
            
        # Calculate or map duration_ms
        if 'duration_ms' in df.columns:
            std_df['duration_ms'] = pd.to_numeric(df['duration_ms'], errors='coerce')
        else:
            std_df['duration_ms'] = std_df['end_ms'] - std_df['start_ms']
            
        # Clean up invalid durations
        std_df.loc[std_df['duration_ms'] < 0, 'duration_ms'] = np.nan
        
        # Drop rows with entirely missing structural info
        std_df.dropna(subset=['event_type', 'start_ms', 'end_ms'], how='all', inplace=True)
        
        # Ensure it meets the CIR specification
        return self.validate_cir(std_df)

def parse_surveycto_audit(filepath: Union[str, Path]) -> pd.DataFrame:
    """Legacy wrapper function. Use SurveyCTOParser().parse() instead."""
    parser = SurveyCTOParser()
    return parser.parse(filepath)
