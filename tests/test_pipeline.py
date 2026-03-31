import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import pytest
from pathlib import Path

# BUG-3 FIX: process_interview() now exists in run_pipeline.py
from run_pipeline import process_interview


def test_process_interview_aggregation(tmp_path):
    """
    Verify that process_interview correctly groups rows by interview_id and
    returns one feature dictionary per interview.
    """
    p = tmp_path / "multi_interview.csv"

    # SurveyCTO format: interview_id, question_id, start_time, end_time, event_type
    # INT_1: 08:00:00 -> 08:00:20  (20 s = 20 000 ms span)
    # INT_2: 09:00:00 -> 09:00:04  ( 4 s =  4 000 ms span)
    csv_content = (
        "interview_id,question_id,start_time,end_time,event_type\n"
        "INT_1,q1,2023-10-01T08:00:00,2023-10-01T08:00:10,Question\n"
        "INT_1,q2,2023-10-01T08:00:15,2023-10-01T08:00:20,Question\n"
        "INT_2,q1,2023-10-01T09:00:00,2023-10-01T09:00:02,Question\n"
        "INT_2,q2,2023-10-01T09:00:02,2023-10-01T09:00:04,Question\n"
    )
    p.write_text(csv_content)

    features_list = process_interview(p, parser_type='surveycto')

    # Expect exactly 2 interview feature sets
    assert len(features_list) == 2, (
        f"Expected 2 interviews, got {len(features_list)}"
    )

    int1 = next(f for f in features_list if f['interview_id'] == 'INT_1')
    int2 = next(f for f in features_list if f['interview_id'] == 'INT_2')

    # BUG-6 FIX: Use actual pipeline key names from thesis Table 3
    # V-01 = max(end_ms) - min(start_ms) for the whole interview
    # INT_1: 08:00:20 - 08:00:00 = 20 000 ms
    assert int1['V-01_total_interview_duration_ms'] == pytest.approx(20000.0, abs=100), (
        f"INT_1 duration wrong: {int1.get('V-01_total_interview_duration_ms')}"
    )

    # INT_2: 09:00:04 - 09:00:00 = 4 000 ms
    assert int2['V-01_total_interview_duration_ms'] == pytest.approx(4000.0, abs=100), (
        f"INT_2 duration wrong: {int2.get('V-01_total_interview_duration_ms')}"
    )

    # BUG-6 FIX: Correct key for back-navigation count (thesis Table 3: V-06)
    # No backward/jump events in the test CSV → count = 0
    assert int1['V-06_back_navigation_total_count'] == 0, (
        f"INT_1 back-nav count wrong: {int1.get('V-06_back_navigation_total_count')}"
    )
    assert int2['V-06_back_navigation_total_count'] == 0, (
        f"INT_2 back-nav count wrong: {int2.get('V-06_back_navigation_total_count')}"
    )


def test_process_interview_returns_list(tmp_path):
    """process_interview must always return a list, never None or a DataFrame."""
    p = tmp_path / "single.csv"
    p.write_text("interview_id,question_id,start_time,end_time,event_type\n"
                 "INT_X,q1,2023-10-01T10:00:00,2023-10-01T10:00:05,Question\n")

    result = process_interview(p, parser_type='surveycto')
    assert isinstance(result, list)


def test_process_interview_empty_file(tmp_path):
    """An empty CSV (header only) must return an empty list, not crash."""
    p = tmp_path / "empty.csv"
    p.write_text("event,node,start,end\n")

    result = process_interview(p, parser_type='surveycto')
    assert isinstance(result, list)
    assert len(result) == 0
