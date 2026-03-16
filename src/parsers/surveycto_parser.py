import pandas as pd
import numpy as np
from pathlib import Path
from typing import Union

def parse_surveycto_audit(filepath: Union[str, Path]) -> pd.DataFrame:
    """
    Parses a SurveyCTO audit CSV file into a standardized DataFrame.
    
    SurveyCTO audit logs typically contain columns: event, node, start, end.
    
    Parameters
    ----------
    filepath : str or Path
        Path to the SurveyCTO audit CSV file.
        
    Returns
    -------
    pd.DataFrame
        Standardized DataFrame containing event timing information.
    """
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        raise ValueError(f"CRITICAL ERROR: Failed to read CSV file '{filepath}'. File may be corrupted or completely empty. Details: {e}")
        
    # Validation constraint: Check if the file is completely missing essential structural columns
    # We require some combination of events, nodes, or times to do any math at all.
    expected_cols = {'event', 'event_type', 'node', 'question_id', 'start', 'start_time', 'end', 'end_time'}
    if not any(col in df.columns for col in expected_cols):
        raise ValueError(f"VALIDATION ERROR: File '{filepath}' does not contain ANY recognized paradata columns. "
                         f"Please ensure your CSV has headers like: {', '.join(expected_cols)}")
        
    # Standardized dataframe
    std_df = pd.DataFrame()
    
    if 'interview_id' in df.columns:
        std_df['interview_id'] = df['interview_id']
    
    if 'event' in df.columns:
        std_df['event_type'] = df['event']
    elif 'event_type' in df.columns:
        std_df['event_type'] = df['event_type']
    else:
        std_df['event_type'] = 'unknown'
        
    if 'node' in df.columns:
        std_df['question_name'] = df['node']
    elif 'question_id' in df.columns:
        std_df['question_name'] = df['question_id']
    else:
        std_df['question_name'] = None
        
    # Process timestamps and durations
    if 'start' in df.columns:
        # SurveyCTO timestamps are often Unix epoch in milliseconds
        std_df['start_time'] = pd.to_datetime(df['start'], unit='ms', errors='coerce')
    elif 'start_time' in df.columns:
        std_df['start_time'] = pd.to_datetime(df['start_time'], errors='coerce')
        
    if 'end' in df.columns:
        std_df['end_time'] = pd.to_datetime(df['end'], unit='ms', errors='coerce')
    elif 'end_time' in df.columns:
        std_df['end_time'] = pd.to_datetime(df['end_time'], errors='coerce')
        
    if 'start' in df.columns and 'end' in df.columns:
        # Calculate duration in milliseconds directly from the raw numbers if possible
        if pd.api.types.is_numeric_dtype(df['start']) and pd.api.types.is_numeric_dtype(df['end']):
            std_df['duration_ms'] = df['end'] - df['start']
        elif 'start_time' in std_df.columns and 'end_time' in std_df.columns:
            std_df['duration_ms'] = (std_df['end_time'] - std_df['start_time']).dt.total_seconds() * 1000
    elif 'start_time' in std_df.columns and 'end_time' in std_df.columns:
        std_df['duration_ms'] = (std_df['end_time'] - std_df['start_time']).dt.total_seconds() * 1000
    else:
        std_df['duration_ms'] = np.nan
        
    # Clean up negatives and extremely small errors due to float precision
    if 'duration_ms' in std_df.columns:
        std_df.loc[std_df['duration_ms'] < 0, 'duration_ms'] = np.nan
        
    return std_df

