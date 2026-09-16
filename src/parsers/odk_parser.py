import pandas as pd
import numpy as np
from pathlib import Path
from typing import Union
from .base_parser import BaseParser


def _datetime_series_to_epoch_ms(values: pd.Series) -> pd.Series:
    """
    Convert ODK ISO timestamps into epoch milliseconds with NaN preservation.
    """
    parsed = pd.to_datetime(values, errors='coerce', utc=True)
    epoch_ms = pd.Series(np.nan, index=values.index, dtype='float64')
    valid_mask = parsed.notna()
    if valid_mask.any():
        # Divide by an explicit one-millisecond Timedelta rather than casting to
        # int64, so the result is epoch milliseconds at any datetime resolution.
        epoch = pd.Timestamp(0, tz='UTC')
        epoch_ms.loc[valid_mask] = (
            (parsed.loc[valid_mask] - epoch) // pd.Timedelta(milliseconds=1)
        ).astype('float64')
    return epoch_ms

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
            
        # Create std_df with the same number of rows as input df
        std_df = pd.DataFrame(index=df.index)
        
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
                std_df['field_name'] = df[col].fillna('unknown_field').astype(str).str.strip()
                break
        if 'field_name' not in std_df.columns:
            std_df['field_name'] = 'unknown_field'
            
        # 3. Event Type
        if 'event' in df.columns:
            std_df['event_type'] = df['event'].fillna('unknown_event').replace({
                'form-start': 'form_start',
                'form-end': 'form_end',
                'question-start': 'field_start',
                'question-end': 'field_end',
                'form start': 'form_start',
                'question': 'field_start',
                'group questions': 'field_start',
                'end screen': 'form_end',
                # Remaining form-level events in ODK's documented audit log.
                # They carry no node, so they are normalised to form_* names
                # and excluded from section statistics alongside form start
                # and form end.
                'form save': 'form_save',
                'form exit': 'form_exit',
                'form resume': 'form_resume',
                'form finalize': 'form_finalize'
            })
        else:
            std_df['event_type'] = 'unknown_event'
            
        # 4. Timing Information
        std_df['start_ms'] = np.nan
        for pt in ['start', 'start_time', 'ts_start']:
            if pt in df.columns:
                s_col = pd.to_numeric(df[pt], errors='coerce')
                if s_col.isna().all() and not df[pt].isna().all():
                    s_col = _datetime_series_to_epoch_ms(df[pt])
                    s_col = s_col.where(s_col > 0, np.nan)
                else:
                    # Numeric epoch data: apply epoch-seconds guard.
                    valid = s_col.dropna()
                    if len(valid) > 0 and valid.median() < 2e10:
                        s_col = s_col * 1000
                std_df['start_ms'] = s_col
                break
                
        std_df['end_ms'] = np.nan
        for pt in ['end', 'end_time', 'ts_end']:
            if pt in df.columns:
                e_col = pd.to_numeric(df[pt], errors='coerce')
                if e_col.isna().all() and not df[pt].isna().all():
                    e_col = _datetime_series_to_epoch_ms(df[pt])
                    e_col = e_col.where(e_col > 0, np.nan)
                else:
                    valid = e_col.dropna()
                    if len(valid) > 0 and valid.median() < 2e10:
                        e_col = e_col * 1000
                std_df['end_ms'] = e_col
                break
            
        # Calculate or map duration_ms
        std_df.loc[:, 'duration_ms'] = std_df['end_ms'] - std_df['start_ms']
            
        # Clean up invalid durations
        std_df.loc[std_df['duration_ms'] < 0, 'duration_ms'] = np.nan

        # Synthetic audit logs may arrive as one file with repeated form-start/end blocks
        # and no explicit interview identifiers. In that case we assign sequential IDs.
        if 'interview_id' not in df.columns and 'instance_id' not in df.columns and 'uuid' not in df.columns:
            if 'event' in df.columns:
                event_strings = df['event'].astype(str).str.lower()
                start_mask = event_strings.isin(['form start', 'form-start'])
                if start_mask.sum() > 1:
                    synthetic_ids = []
                    current = 0
                    for ev in event_strings:
                        if ev in ['form start', 'form-start']:
                            current += 1
                        synthetic_ids.append(f"INT-{current:05d}")
                    std_df['interview_id'] = synthetic_ids

        # Drop rows with entirely missing structural info
        std_df.dropna(subset=['event_type', 'start_ms', 'end_ms'], how='all', inplace=True)
        
        # Ensure it meets the CIR specification
        return self.validate_cir(std_df)

def parse_odk_audit(filepath: Union[str, Path]) -> pd.DataFrame:
    """Legacy wrapper function. Use ODKParser().parse() instead."""
    parser = ODKParser()
    return parser.parse(filepath)
