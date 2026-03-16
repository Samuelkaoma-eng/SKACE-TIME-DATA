import pandas as pd
import numpy as np
from pathlib import Path
from typing import Union

def parse_odk_audit(filepath: Union[str, Path]) -> pd.DataFrame:
    """
    Parses an ODK Collect audit CSV file into a standardized DataFrame.
    
    ODK audit logs typically contain columns: event, node, start, end.
    The structure is very similar to SurveyCTO.
    
    Parameters
    ----------
    filepath : str or Path
        Path to the ODK audit CSV file.
        
    Returns
    -------
    pd.DataFrame
        Standardized DataFrame containing event timing information.
    """
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        raise ValueError(f"Error reading ODK audit file {filepath}: {e}")
        
    std_df = pd.DataFrame()
    
    if 'event' in df.columns:
        std_df['event_type'] = df['event']
    else:
        std_df['event_type'] = 'unknown'
        
    if 'node' in df.columns:
        std_df['question_name'] = df['node']
    else:
        std_df['question_name'] = None
        
    # Process timestamps
    if 'start' in df.columns:
        std_df['start_time'] = pd.to_datetime(df['start'], unit='ms', errors='coerce')
        
    if 'end' in df.columns:
        std_df['end_time'] = pd.to_datetime(df['end'], unit='ms', errors='coerce')
        
    if 'start' in df.columns and 'end' in df.columns:
        if pd.api.types.is_numeric_dtype(df['start']) and pd.api.types.is_numeric_dtype(df['end']):
            std_df['duration_ms'] = df['end'] - df['start']
        elif 'start_time' in std_df.columns and 'end_time' in std_df.columns:
            std_df['duration_ms'] = (std_df['end_time'] - std_df['start_time']).dt.total_seconds() * 1000
    else:
        std_df['duration_ms'] = np.nan
        
    if 'duration_ms' in std_df.columns:
        std_df.loc[std_df['duration_ms'] < 0, 'duration_ms'] = np.nan
        
    return std_df

