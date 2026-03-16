import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
import pytest

from src.features.response_time import calculate_basic_timing
from run_pipeline import process_interview

def test_missing_timestamps():
    df = pd.DataFrame({
        'event_type': ['Question', 'Question'],
        'duration_ms': [np.nan, np.nan]
    })
    
    res = calculate_basic_timing(df)
    assert np.isnan(res['mean_response_time_ms'])
    assert np.isnan(res['variance_response_time_ms'])
    # Entropy should be 0 or NaN if there's no data
    assert res['entropy_response_time'] == 0.0 or np.isnan(res['entropy_response_time'])

def test_single_question_interview():
    df = pd.DataFrame({
        'event_type': ['Question'],
        'duration_ms': [5000]
    })
    
    res = calculate_basic_timing(df)
    assert res['mean_response_time_ms'] == 5000.0
    assert res['variance_response_time_ms'] == 0.0 # Variance of 1 item is 0

def test_negative_durations_handled_by_parser(tmp_path):
    p = tmp_path / "extreme_audit.csv"
    # End time before start
    p.write_text("interview_id,event_type,start_time,end_time\n1,Q,2023-01-01T10:00:10,2023-01-01T10:00:00\n")
    
    features_list = process_interview(p, parser_type='surveycto')
    assert len(features_list) == 1
    # Parser should convert negative durations to NaN, meaning mean_response_time is NaN
    assert np.isnan(features_list[0]['mean_response_time_ms'])

def test_large_dataset_performance():
    # Stress test with 100,000 rows
    np.random.seed(42)
    n_rows = 100000
    df = pd.DataFrame({
        'interview_id': ['INT_1'] * n_rows,
        'event_type': ['Question'] * n_rows,
        'duration_ms': np.random.randint(1000, 60000, n_rows)
    })
    
    # Should complete without memory errors or crashing
    res = calculate_basic_timing(df)
    assert res['total_duration_ms'] > 0
    assert res['mean_response_time_ms'] > 0
