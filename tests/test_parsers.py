import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
import pytest
from pathlib import Path

# Assume parsers are correctly imported
from src.parsers.surveycto_parser import parse_surveycto_audit
from src.parsers.odk_parser import parse_odk_audit

def test_surveycto_parser_empty_file(tmp_path):
    # Setup mock CSV
    p = tmp_path / "empty_audit.csv"
    p.write_text("event,node,start,end\n")
    
    df = parse_surveycto_audit(p)
    assert isinstance(df, pd.DataFrame)
    assert df.empty

def test_surveycto_parser_valid_data(tmp_path):
    # Setup mock CSV
    p = tmp_path / "valid_audit.csv"
    p.write_text("event,node,start,end\nQuestion,q1,1600000000000,1600000001000\n")
    
    df = parse_surveycto_audit(p)
    assert not df.empty
    assert 'duration_ms' in df.columns
    assert df.iloc[0]['duration_ms'] == 1000.0

def test_odk_parser_negative_duration(tmp_path):
    p = tmp_path / "neg_audit.csv"
    # End time is before start time
    p.write_text("event,node,start,end\nQuestion,q1,1600000001000,1600000000000\n")
    
    df = parse_odk_audit(p)
    assert pd.isna(df.iloc[0]['duration_ms'])
