import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.features.question_features import QuestionFeatureExtractor
from src.features.section_features import SectionFeatureExtractor
from src.features.statistical_features import StatisticalFeatureExtractor
from src.features.survey_features import SurveyFeatureExtractor


def _cir_frame() -> pd.DataFrame:
    rows = [
        ("INT1", "demographics_q01", "question-end", 0, 1000),
        ("INT1", "household_q01", "question-end", 1500, 3500),
        ("INT1", "demographics_q01", "question-end", 5000, 6500),
        ("INT1", "demographics_q02", "jump", 7000, 7300),
        ("INT1", "demographics_q02", "question-end", 8000, 12000),
    ]
    df = pd.DataFrame(
        rows,
        columns=["interview_id", "field_name", "event_type", "start_ms", "end_ms"],
    )
    df.loc[:, "duration_ms"] = df["end_ms"] - df["start_ms"]
    return df


def test_question_features_preserve_field_level_behavior():
    features = QuestionFeatureExtractor().extract(_cir_frame())

    assert set(features.index) == {"demographics_q01", "household_q01", "demographics_q02"}
    # Q-01 sums the two active visits (1000 ms + 1500 ms); the gap between
    # them is excluded from active response time but included in Q-10.
    assert features.loc["demographics_q01", "Q-01_response_time_ms"] == pytest.approx(2500)
    assert features.loc["demographics_q01", "Q-10_first_to_last_interaction_duration"] == pytest.approx(6500)
    assert features.loc["demographics_q01", "Q-04_revisit_flag"] == 1
    assert features.loc["demographics_q01", "Q-05_revisit_count"] == 1
    assert features.loc["demographics_q02", "Q-01_response_time_ms"] == pytest.approx(4000)


def test_section_features_infer_section_names_and_variance():
    cir = _cir_frame()
    q_features = QuestionFeatureExtractor().extract(cir)
    section_features = SectionFeatureExtractor().extract(cir, q_features)

    assert SectionFeatureExtractor._infer_section_name("/data/household/q_name") == "household"
    assert SectionFeatureExtractor._infer_section_name("/data/q_name") == "MainSection"
    assert SectionFeatureExtractor._infer_section_name("demographics_q01") == "demographics"
    assert SectionFeatureExtractor._infer_section_name("plainfield") == "MainSection"
    assert set(section_features.index) == {"demographics", "household"}
    assert section_features.loc["demographics", "S-03_within_section_variance"] > 0


def test_survey_features_convert_epoch_milliseconds_safely():
    cir = _cir_frame()
    cir.loc[:, "start_ms"] = cir["start_ms"] + 1672646400000
    cir.loc[:, "end_ms"] = cir["end_ms"] + 1672646400000

    features = SurveyFeatureExtractor().extract(cir)

    assert features["V-01_total_interview_duration_ms"] == pytest.approx(12000)
    assert features["V-07_time_of_day_hour"] == 8
    assert features["V-08_day_of_week"] == 0


def test_statistical_features_are_computed_from_question_times():
    q_features = pd.DataFrame(
        {"Q-01_response_time_ms": [1000.0, 2000.0, 4000.0]},
        index=["q1", "q2", "q3"],
    )

    features = StatisticalFeatureExtractor().extract(q_features)

    assert features["T-01_rt_variance"] == pytest.approx(np.var([1000, 2000, 4000], ddof=1))
    assert features["T-02_rt_iqr"] == pytest.approx(1500)
    assert features["T-06_rt_mean"] == pytest.approx(2333.3333333333335)
    assert features["T-09_rt_min"] == pytest.approx(1000)
    assert features["T-10_rt_max"] == pytest.approx(4000)
