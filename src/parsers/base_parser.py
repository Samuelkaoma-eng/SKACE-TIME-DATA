import pandas as pd
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union

class BaseParser(ABC):
    """
    Abstract Base Class for parsing diverse paradata formats into a 
    Common Intermediate Representation (CIR).
    
    The CIR guarantees the following columns exist (in milliseconds where applicable):
    - interview_id
    - field_name
    - event_type
    - start_ms
    - end_ms
    - duration_ms
    """
    
    REQUIRED_COLUMNS = [
        'interview_id',
        'field_name',
        'event_type',
        'start_ms',
        'end_ms',
        'duration_ms'
    ]

    @abstractmethod
    def parse(self, filepath: Union[str, Path]) -> pd.DataFrame:
        """
        Parses the specific raw audit log file and returns it in CIR format.
        
        Parameters
        ----------
        filepath : str or Path
            Path to the raw audit log CSV file.
            
        Returns
        -------
        pd.DataFrame
            The standardized CIR DataFrame.
        """
        pass

    def validate_cir(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ensures the extracted DataFrame perfectly matches the CIR schema.
        Throws helpful Error if columns are missing.
        """
        missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            raise ValueError(f"CRITICAL: Parser failed to generate CIR required columns: {missing_cols}")
            
        # Optional: Reorder columns for consistency
        return df[self.REQUIRED_COLUMNS].copy()
