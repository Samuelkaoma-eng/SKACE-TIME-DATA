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


def test_section_features_exclude_administrative_form_events():
    # Regression: form-level start and end rows carry a blank field name. If
    # they reach section aggregation they form a pseudo-section whose gap
    # spans the whole interview and swamps every pause statistic.
    questions = _cir_frame()
    admin = pd.DataFrame(
        [
            ("INT1", "unknown_field", "form_start", -2000, -1000),
            ("INT1", "unknown_field", "form_end", 60000, 61000),
        ],
        columns=["interview_id", "field_name", "event_type", "start_ms", "end_ms"],
    )
    admin.loc[:, "duration_ms"] = admin["end_ms"] - admin["start_ms"]
    with_admin = pd.concat([admin.iloc[[0]], questions, admin.iloc[[1]]], ignore_index=True)

    q_features = QuestionFeatureExtractor().extract(questions)
    expected = SectionFeatureExtractor().extract(questions, q_features)
    actual = SectionFeatureExtractor().extract(with_admin, q_features)

    assert "MainSection" not in actual.index
    assert set(actual.index) == {"demographics", "household"}
    pd.testing.assert_frame_equal(actual.sort_index(), expected.sort_index())


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


def _rich_cir_frame() -> pd.DataFrame:
    """CIR exercising the feature paths the smaller fixture leaves untouched:
    explicit start/end markers, a constraint event, internal gaps within a
    field, and a long gap between fields in the same section."""
    rows = [
        ("INT1", "demographics_q01", "question-start", 0, 0),
        ("INT1", "demographics_q01", "constraint_error", 200, 250),
        ("INT1", "demographics_q01", "question-end", 500, 2000),
        ("INT1", "demographics_q02", "question-end", 8000, 12000),
        ("INT1", "household_q01", "question-end", 20000, 23000),
    ]
    df = pd.DataFrame(
        rows,
        columns=["interview_id", "field_name", "event_type", "start_ms", "end_ms"],
    )
    df.loc[:, "duration_ms"] = df["end_ms"] - df["start_ms"]
    return df


def test_question_features_timing_edit_and_constraint_counts():
    features = QuestionFeatureExtractor().extract(_rich_cir_frame())
    q01 = features.loc["demographics_q01"]
    q02 = features.loc["demographics_q02"]

    # Q-02 uses the explicit markers: first question-end start (500) minus
    # first question-start start (0).
    assert q01["Q-02_time_to_first_interaction"] == pytest.approx(500)
    # With no start/end markers the fallback is the first event's duration.
    assert q02["Q-02_time_to_first_interaction"] == pytest.approx(4000)

    # Q-03 counts events beyond the first as edits within the visit.
    assert q01["Q-03_edit_count"] == 2
    assert q02["Q-03_edit_count"] == 0

    # Q-07 sums the positive gaps between consecutive events on the field:
    # (200 - 0) + (500 - 250) = 450.
    assert q01["Q-07_idle_time_ms"] == pytest.approx(450)
    assert q02["Q-07_idle_time_ms"] == pytest.approx(0)

    # Q-08 is the raw event count on the field.
    assert q01["Q-08_keystroke_count"] == 3
    assert q02["Q-08_keystroke_count"] == 1

    # Q-09 matches error, constraint or invalid in the event type.
    assert q01["Q-09_constraint_trigger_count"] == 1
    assert q02["Q-09_constraint_trigger_count"] == 0


def test_section_features_pace_duration_and_pauses():
    cir = _rich_cir_frame()
    q_features = QuestionFeatureExtractor().extract(cir)
    sections = SectionFeatureExtractor().extract(cir, q_features)

    demo = sections.loc["demographics"]
    house = sections.loc["household"]

    # S-01 is the mean Q-01 across the section's questions.
    # demographics_q01 sums 0 + 50 + 1500 = 1550; demographics_q02 is 4000.
    assert demo["S-01_mean_section_pace"] == pytest.approx((1550 + 4000) / 2)
    assert house["S-01_mean_section_pace"] == pytest.approx(3000)

    # S-02 spans the section's first start to its last end.
    assert demo["S-02_section_duration_ms"] == pytest.approx(12000)
    assert house["S-02_section_duration_ms"] == pytest.approx(3000)

    # Pauses are the positive gaps between consecutive section events:
    # 200, 250 and 6000.
    assert demo["S-07_mean_pause_duration_ms"] == pytest.approx((200 + 250 + 6000) / 3)
    assert demo["S-08_max_pause_duration_ms"] == pytest.approx(6000)
    # A single-event section has no gaps to measure.
    assert house["S-07_mean_pause_duration_ms"] == pytest.approx(0)
    assert house["S-08_max_pause_duration_ms"] == pytest.approx(0)


def test_survey_speed_trajectory_splits_interview_into_thirds():
    rows = [
        ("INT1", f"q{i:02d}", "field_end", start, end)
        for i, (start, end) in enumerate(
            [(0, 1000), (1000, 2000), (2000, 3000), (3000, 5000), (5000, 7000), (7000, 9000)]
        )
    ]
    df = pd.DataFrame(
        rows, columns=["interview_id", "field_name", "event_type", "start_ms", "end_ms"]
    )
    df.loc[:, "duration_ms"] = df["end_ms"] - df["start_ms"]

    features = SurveyFeatureExtractor().extract(df)

    # Six events give a third of two. The early slice spans 0 to 2000 over two
    # completed fields, the late slice 5000 to 9000 over two.
    assert features["V-02_speed_trajectory_early"] == pytest.approx(1000)
    assert features["V-03_speed_trajectory_late"] == pytest.approx(2000)
    # The interview slows down, so the ratio exceeds one.
    assert features["V-04_speed_trajectory_ratio"] == pytest.approx(2.0)


def test_session_length_vs_median_is_relative_to_the_cohort(tmp_path):
    # V-09 is assigned by the controller rather than the survey extractor,
    # because it needs the median across the cohort rather than one interview.
    # Three interviews of 20, 40 and 60 seconds give a median of 40 seconds, so
    # the ratios must come out at 0.5, 1.0 and 1.5.
    from src.pipeline.controller import PipelineController

    path = tmp_path / "cohort.csv"
    path.write_text(
        """interview_id,question_id,start_time,end_time,event_type
INT_A,demographics_q1,2023-10-01T08:00:00,2023-10-01T08:00:10,Question
INT_A,economics_q2,2023-10-01T08:00:10,2023-10-01T08:00:20,Question
INT_B,demographics_q1,2023-10-01T09:00:00,2023-10-01T09:00:20,Question
INT_B,economics_q2,2023-10-01T09:00:20,2023-10-01T09:00:40,Question
INT_C,demographics_q1,2023-10-01T10:00:00,2023-10-01T10:00:30,Question
INT_C,economics_q2,2023-10-01T10:00:30,2023-10-01T10:01:00,Question
"""
    )

    controller = PipelineController(parser_type="surveycto")
    # V-09 is filled in at batch level, because the median is a property of
    # the cohort rather than of any one file, so process_batch_detailed is the
    # entry point that populates it.
    interviews = pd.DataFrame(controller.process_batch_detailed([path])["interview_features"])
    interviews = interviews.set_index("interview_id")

    assert interviews["V-01_total_interview_duration_ms"].median() == pytest.approx(40_000)
    assert interviews.loc["INT_A", "V-09_session_length_vs_median"] == pytest.approx(0.5)
    assert interviews.loc["INT_B", "V-09_session_length_vs_median"] == pytest.approx(1.0)
    assert interviews.loc["INT_C", "V-09_session_length_vs_median"] == pytest.approx(1.5)
