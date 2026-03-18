import pandas as pd
import numpy as np
from pathlib import Path
from typing import Union
from .base_parser import BaseParser

class ODKParser(BaseParser):
    """
    Parser for ODK Collect audit logs.
    Converts ODK log structures into the standardized CIR.
    """
    
    def parse(self, filepath: Union[str, Path]) -> pd.DataFrame:
        filepath = Path(filepath)
        try:
            df = pd.read_csv(filepath, comment='#')
            df.dropna(how='all', inplace=True)
        except Exception as e:
            raise ValueError(f"CRITICAL ERROR: Failed to read ODK CSV file '{filepath}'. Details: {e}")
            
        std_df = pd.DataFrame()
        
        # 1. Interview ID
        if 'interview_id' in df.columns:
            std_df['interview_id'] = df['interview_id']
        elif 'instance_id' in df.columns:
             std_df['interview_id'] = df['instance_id']
        else:
            std_df['interview_id'] = filepath.stem
            
        # 2. Field Name
        for col in ['node', 'name', 'field']:
            if col in df.columns:
                std_df['field_name'] = df[col].astype(str).str.strip().fillna('unknown_field')
                break
        if 'field_name' not in std_df.columns:
            std_df['field_name'] = 'unknown_field'
            
        # 3. Event Type
        if 'event' in df.columns:
            std_df['event_type'] = df['event'].fillna('unknown_event').replace({
                'form-start': 'form_start',
                'form-end': 'form_end',
                'question-start': 'field_start',
                'question-end': 'field_end'
            })
        else:
            std_df['event_type'] = 'unknown_event'
            
        # 4. Timing Information
        std_df['start_ms'] = np.nan
        for pt in ['start', 'start_time', 'ts_start']:
            if pt in df.columns:
                s_col = pd.to_numeric(df[pt], errors='coerce')
                if s_col.isna().all() and not df[pt].isna().all():
                    s_col = pd.to_datetime(df[pt], errors='coerce', format='mixed').astype('datetime64[ms]').astype('int64')
                    s_col.loc[s_col < 0] = np.nan
                std_df['start_ms'] = s_col
                break
                
        std_df['end_ms'] = np.nan
        for pt in ['end', 'end_time', 'ts_end']:
            if pt in df.columns:
                e_col = pd.to_numeric(df[pt], errors='coerce')
                if e_col.isna().all() and not df[pt].isna().all():
                    e_col = pd.to_datetime(df[pt], errors='coerce', format='mixed').astype('datetime64[ms]').astype('int64')
                    e_col.loc[e_col < 0] = np.nan
                std_df['end_ms'] = e_col
                break
            
        # Calculate or map duration_ms
        std_df['duration_ms'] = std_df['end_ms'] - std_df['start_ms']
            
        # Clean up invalid durations
        std_df.loc[std_df['duration_ms'] < 0, 'duration_ms'] = np.nan
        
        # Drop rows with entirely missing structural info
        std_df.dropna(subset=['event_type', 'start_ms', 'end_ms'], how='all', inplace=True)
        
        # Ensure it meets the CIR specification
        return self.validate_cir(std_df)

def parse_odk_audit(filepath: Union[str, Path]) -> pd.DataFrame:
    """Legacy wrapper function. Use ODKParser().parse() instead."""
    parser = ODKParser()
    return parser.parse(filepath)
