import os
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from run_pipeline import main as run_pipeline_main, process_interview
from src.pipeline.controller import PipelineController
from src.parsers.odk_parser import ODKParser
from src.parsers.surveycto_parser import SurveyCTOParser


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

    # V-01 = max(end_ms) - min(start_ms) for the whole interview.
    # INT_1: 08:00:20 - 08:00:00 = 20 000 ms
    assert int1['V-01_total_interview_duration_ms'] == pytest.approx(20000.0, abs=100), (
        f"INT_1 duration wrong: {int1.get('V-01_total_interview_duration_ms')}"
    )

    # INT_2: 09:00:04 - 09:00:00 = 4 000 ms
    assert int2['V-01_total_interview_duration_ms'] == pytest.approx(4000.0, abs=100), (
        f"INT_2 duration wrong: {int2.get('V-01_total_interview_duration_ms')}"
    )

    # No backward/jump events in the test CSV, so the count should be 0.
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


def test_process_file_detailed_preserves_question_and_section_grain(tmp_path):
    p = tmp_path / "granular.csv"
    p.write_text(
        "interview_id,question_id,start_time,end_time,event_type\n"
        "INT_A,demographics_q1,2023-10-01T08:00:00,2023-10-01T08:00:04,Question\n"
        "INT_A,economics_q2,2023-10-01T08:00:05,2023-10-01T08:00:11,Question\n"
        "INT_B,demographics_q1,2023-10-01T09:00:00,2023-10-01T09:00:03,Question\n"
        "INT_B,economics_q2,2023-10-01T09:00:05,2023-10-01T09:00:09,Question\n"
    )

    controller = PipelineController(parser_type="surveycto")
    detailed = controller.process_file_detailed(p)

    assert len(detailed["interview_features"]) == 2

    question_features = detailed["question_features"]
    section_features = detailed["section_features"]

    assert list(question_features.columns[:3]) == ["file_name", "interview_id", "field_name"]
    assert list(section_features.columns[:3]) == ["file_name", "interview_id", "section_name"]

    assert len(question_features) == 4
    assert set(question_features["field_name"]) == {"demographics_q1", "economics_q2"}

    assert len(section_features) == 4
    assert set(section_features["section_name"]) == {"demographics", "economics"}


def test_process_batch_detailed_returns_granular_tables(tmp_path):
    p = tmp_path / "batch.csv"
    p.write_text(
        "interview_id,question_id,start_time,end_time,event_type\n"
        "INT_A,demographics_q1,2023-10-01T08:00:00,2023-10-01T08:00:04,Question\n"
        "INT_A,economics_q2,2023-10-01T08:00:05,2023-10-01T08:00:11,Question\n"
        "INT_B,demographics_q1,2023-10-01T09:00:00,2023-10-01T09:00:03,Question\n"
        "INT_B,economics_q2,2023-10-01T09:00:05,2023-10-01T09:00:09,Question\n"
    )

    controller = PipelineController(parser_type="surveycto")
    detailed = controller.process_batch_detailed([p])

    interview_df = detailed["interview_features"]
    question_features = detailed["question_features"]
    section_features = detailed["section_features"]

    assert isinstance(interview_df, pd.DataFrame)
    assert len(interview_df) == 2
    assert "anomaly_score" in interview_df.columns

    assert len(question_features) == 4
    assert len(section_features) == 4


def test_run_pipeline_writes_granular_output_files(tmp_path, monkeypatch):
    input_path = tmp_path / "cli_input.csv"
    output_dir = tmp_path / "output"
    input_path.write_text(
        "interview_id,question_id,start_time,end_time,event_type\n"
        "INT_A,demographics_q1,2023-10-01T08:00:00,2023-10-01T08:00:04,Question\n"
        "INT_A,economics_q2,2023-10-01T08:00:05,2023-10-01T08:00:11,Question\n"
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_pipeline.py",
            "--parser",
            "surveycto",
            "--output-dir",
            str(output_dir),
            "--label",
            "granular_cli",
            "--inputs",
            str(input_path),
        ],
    )

    exit_code = run_pipeline_main()

    assert exit_code == 0
    assert (output_dir / "question_features_granular_cli.csv").exists()
    assert (output_dir / "section_features_granular_cli.csv").exists()
    assert (output_dir / "feature_dataset_granular_cli.csv").exists()
    assert (output_dir / "anomaly_report_granular_cli.csv").exists()
    assert (output_dir / "pipeline_output_granular_cli.csv").exists()


def test_auto_parser_detects_iso_timestamp_file_as_odk(tmp_path, monkeypatch):
    p = tmp_path / "odk_like.csv"
    p.write_text(
        "event,node,start,end\n"
        "form start,/data/root,2024-03-29T14:42:47.397,2024-03-29T14:42:49.086\n"
    )

    called = {"odk": 0, "surveycto": 0}

    def fake_odk_parse(self, filepath):
        called["odk"] += 1
        return pd.DataFrame(
            {
                "interview_id": ["ODK-1"],
                "field_name": ["root"],
                "event_type": ["form_start"],
                "start_ms": [1],
                "end_ms": [2],
                "duration_ms": [1],
            }
        )

    def fake_scto_parse(self, filepath):
        called["surveycto"] += 1
        return pd.DataFrame(
            {
                "interview_id": ["SCTO-1"],
                "field_name": ["root"],
                "event_type": ["form_start"],
                "start_ms": [1],
                "end_ms": [2],
                "duration_ms": [1],
            }
        )

    monkeypatch.setattr(ODKParser, "parse", fake_odk_parse)
    monkeypatch.setattr(SurveyCTOParser, "parse", fake_scto_parse)

    controller = PipelineController(parser_type="auto")
    controller.process_file(p)

    assert called["odk"] == 1
    assert called["surveycto"] == 0
