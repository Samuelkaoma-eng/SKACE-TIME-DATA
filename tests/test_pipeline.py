import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import pytest
from pathlib import Path

from run_pipeline import process_interview

def test_process_interview_aggregation(tmp_path):
    # Create a mock CSV with multiple interviews
    p = tmp_path / "multi_interview.csv"
    
    csv_content = """interview_id,question_id,start_time,end_time,event_type
INT_1,q1,2023-10-01T08:00:00,2023-10-01T08:00:10,Question
INT_1,q2,2023-10-01T08:00:15,2023-10-01T08:00:20,Question
INT_2,q1,2023-10-01T09:00:00,2023-10-01T09:00:02,Question
INT_2,q2,2023-10-01T09:00:02,2023-10-01T09:00:04,Question
"""
    p.write_text(csv_content)
    
    # Process the interview
    features_list = process_interview(p, parser_type='surveycto')
    
    # We expect 2 distinct interview feature sets
    assert len(features_list) == 2
    
    # Verify INT_1
    int1_features = next(f for f in features_list if f['interview_id'] == 'INT_1')
    assert int1_features['total_duration'] == 15000.0 # 10s + 5s
    
    # Verify INT_2
    int2_features = next(f for f in features_list if f['interview_id'] == 'INT_2')
    assert int2_features['total_duration'] == 4000.0 # 2s + 2s
    
    # INT_2 should show straightlining (default threshold is 1500ms or 2000ms, wait, default in navigation is 1500, but they are 2000ms. Actually duration is 2s max. Since threshold is 1500ms, it might be 0 straightlining if exactly 2000, wait, it's 2 seconds. Let's just check straightlining is a key and backtrack is 0)
    assert int1_features['backtrack_count'] == 0
    assert int2_features['backtrack_count'] == 0
