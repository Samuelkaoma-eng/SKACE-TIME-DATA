import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
import pytest
from hypothesis import given, strategies as st

from src.features.response_time import calculate_basic_timing, calculate_speed_index
from src.features.pauses import calculate_pauses
from src.features.navigation import calculate_navigation_metrics
from src.features.rhythm import calculate_rhythm_metrics
from src.features.section_features import SectionFeatureExtractor

def test_calculate_basic_timing_empty():
    df = pd.DataFrame()
    res = calculate_basic_timing(df)
    assert np.isnan(res['mean_response_time'])

def test_calculate_basic_timing_valid():
    df = pd.DataFrame({'duration_ms': [1000, 2000, 3000]})
    res = calculate_basic_timing(df)
    assert res['mean_response_time'] == 2000.0
    assert res['median_response_time'] == 2000.0
    assert res['total_duration'] == 6000.0

@given(st.floats(min_value=0.1, max_value=1e6), st.floats(min_value=0.1, max_value=1e6))
def test_speed_index_properties(interview_dur, median_dur):
    idx = calculate_speed_index(interview_dur, median_dur)
    assert idx >= 0
    if interview_dur < median_dur:
        assert idx < 1.0
    elif interview_dur > median_dur:
        assert idx > 1.0

def test_calculate_pauses():
    # Construct a dataframe with a 2-second gap
    df = pd.DataFrame({
        'start_time': pd.to_datetime(['2023-01-01 10:00:00', '2023-01-01 10:00:05']),
        'end_time': pd.to_datetime(['2023-01-01 10:00:01', '2023-01-01 10:00:06'])
    })
    
    # Gap is 4 seconds (10:00:01 to 10:00:05), threshold is 3 seconds
    res = calculate_pauses(df, pause_threshold_ms=3000)
    assert res['pause_count'] == 1
    assert res['total_pause_duration'] == 4000.0

def test_calculate_navigation_metrics():
    df = pd.DataFrame({
        'event_type': ['Question', 'Question', 'backward', 'Question'],
        'duration_ms': [5000, 1000, 2000, 800]
    })
    
    res = calculate_navigation_metrics(df, straightline_threshold_ms=1500)
    assert res['backtrack_count'] == 1
    assert res['straightlining_count'] == 2  # 1000ms and 800ms are below 1500ms

def test_calculate_rhythm_metrics():
    df = pd.DataFrame({
        'start_time': pd.to_datetime(['2023-01-01 10:00:00', '2023-01-01 10:00:10', '2023-01-01 10:00:20']),
        'duration_ms': [5000, 5000, 5000]
    })
    
    # Constant duration should yield 0 variance
    res = calculate_rhythm_metrics(df, window_size=3)
    assert res['rolling_variance_mean'] == 0.0
    assert res['rolling_variance_max'] == 0.0


def test_infer_section_name_handles_xpath_and_flat_names():
    infer = SectionFeatureExtractor._infer_section_name

    assert infer('/data/household/q_name') == 'household'
    assert infer('/data/q_name') == 'MainSection'
    assert infer('demographics_q01') == 'demographics'
    assert infer('plainfield') == 'MainSection'
