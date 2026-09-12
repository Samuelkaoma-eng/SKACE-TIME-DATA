import json
import os
import sys
from argparse import Namespace
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from run_pipeline import build_detector_config_from_args
from tests.generate_benchmark_datasets import build_dataset
from scripts.feature_validation import cohens_d, compute_feature_stats
from src.validation.anomaly_detector import AnomalyDetector
from src.validation.detector_config import (
    build_recalibrated_detector_config,
    load_detector_config,
)


def test_compute_feature_stats_reports_cohens_d_and_excludes_detector_outputs():
    eval_df = pd.DataFrame(
        {
            "interview_id": [f"INT{i}" for i in range(8)],
            "ground_truth_is_anomalous": [0, 0, 0, 0, 1, 1, 1, 1],
            "demo_feature": [1.0, 2.0, 3.0, 4.0, 8.0, 9.0, 10.0, 11.0],
            "flag_low_entropy": [0, 0, 0, 0, 1, 1, 1, 1],
            "anomaly_score": [0, 0, 0, 0, 3, 3, 3, 3],
        }
    )

    stats_df = compute_feature_stats(eval_df, alpha=0.05)

    assert set(stats_df["feature"]) == {"demo_feature"}
    row = stats_df.iloc[0]
    expected_d = cohens_d(
        eval_df.loc[eval_df["ground_truth_is_anomalous"] == 0, "demo_feature"],
        eval_df.loc[eval_df["ground_truth_is_anomalous"] == 1, "demo_feature"],
    )
    assert row["effect_size_method"] == "cohens_d"
    assert row["effect_size"] == pytest.approx(expected_d)
    assert row["cohens_d"] == pytest.approx(expected_d)
    assert row["abs_cohens_d"] == pytest.approx(abs(expected_d))


def test_detector_score_contract_for_fabricated_and_normal_profiles():
    normal_rows = []
    for idx in range(6):
        normal_rows.append(
            {
                "interview_id": f"N{idx}",
                "V-01_total_interview_duration_ms": 160000,
                "V-04_speed_trajectory_ratio": 1.0,
                "V-05_back_navigation_rate": 0.05,
                "V-06_back_navigation_total_count": 3,
                "V-07_time_of_day_hour": 8,
                "T-01_rt_variance": 1000000,
                "T-02_rt_iqr": 5000,
                "T-03_rt_entropy": 2.5,
                "T-06_rt_mean": 8000,
                "T-08_rt_cv": 0.5,
                "T-09_rt_min": 3000,
                "T-10_rt_max": 15000,
                "S-03_within_section_variance": 1000000,
            }
        )

    fabricated_rows = []
    for idx in range(4):
        fabricated_rows.append(
            {
                "interview_id": f"F{idx}",
                "V-01_total_interview_duration_ms": 50000,
                "V-04_speed_trajectory_ratio": 1.0,
                "V-05_back_navigation_rate": 0.0,
                "V-06_back_navigation_total_count": 0,
                "V-07_time_of_day_hour": 8,
                "T-01_rt_variance": 100,
                "T-02_rt_iqr": 100,
                "T-03_rt_entropy": 0.1,
                "T-06_rt_mean": 1200,
                "T-08_rt_cv": 0.05,
                "T-09_rt_min": 1000,
                "T-10_rt_max": 1400,
                "S-03_within_section_variance": 2000,
            }
        )

    detected = AnomalyDetector().detect(pd.DataFrame(normal_rows + fabricated_rows))
    normal = detected[detected["interview_id"].str.startswith("N")]
    fabricated = detected[detected["interview_id"].str.startswith("F")]

    assert (normal["anomaly_score"] <= 1).all()
    assert (normal["status"] == "CLEAN").all()
    assert (fabricated["anomaly_score"] >= 5).all()
    assert (fabricated["status"] == "FLAGGED").all()
    assert (fabricated["anomaly_score"] == fabricated["iqr_flags"] + fabricated["rule_flags"]).all()


def test_detector_preserves_upstream_data_quality_flag():
    # Regression: the detector used to overwrite is_data_quality_issue, losing
    # the controller's hierarchical integrity check raised upstream.
    rows = [
        {
            "interview_id": f"N{idx}",
            "V-01_total_interview_duration_ms": 160000 + idx * 1000,
            "V-04_speed_trajectory_ratio": 1.0,
            "T-06_rt_mean": 8000,
            "is_data_quality_issue": 1 if idx == 0 else 0,
        }
        for idx in range(6)
    ]
    detected = AnomalyDetector().detect(pd.DataFrame(rows)).set_index("interview_id")

    assert detected.loc["N0", "is_data_quality_issue"] == 1
    assert detected.loc["N0", "anomaly_category"] == "dq_issue"
    assert (detected.drop(index="N0")["is_data_quality_issue"] == 0).all()


def test_iqr_multiplier_is_configurable(tmp_path):
    durations = [100, 102, 104, 106, 108, 110, 112, 114, 150]
    frame = pd.DataFrame(
        {
            "interview_id": [f"I{idx}" for idx in range(len(durations))],
            "V-01_total_interview_duration_ms": durations,
        }
    )

    assert AnomalyDetector().iqr_multiplier == AnomalyDetector.IQR_MULTIPLIER == 1.5
    default = AnomalyDetector().detect(frame)
    wide = AnomalyDetector(iqr_multiplier=5.0).detect(frame)
    assert default["flag_iqr_duration"].iloc[-1] == 1
    assert wide["flag_iqr_duration"].iloc[-1] == 0

    config_path = tmp_path / "detector_config.json"
    config_path.write_text(json.dumps({"anomaly_detector": {"iqr_multiplier": 3.0}}), encoding="utf-8")
    assert load_detector_config(config_path) == {"iqr_multiplier": 3.0}
    with pytest.raises(ValueError):
        AnomalyDetector(iqr_multiplier=0)


def test_build_recalibrated_detector_config_preserves_threshold_order():
    payload = build_recalibrated_detector_config(
        behavior_score_threshold=6.0,
        data_paths=["data/example.csv"],
        ground_truth_path="data/labels.csv",
        base_config={"anomalous_score_threshold": 5.0},
    )

    detector_config = payload["anomaly_detector"]
    assert detector_config["behavior_score_threshold"] == pytest.approx(6.0)
    assert detector_config["anomalous_score_threshold"] >= detector_config["behavior_score_threshold"]


def test_load_detector_config_reads_supported_detector_settings(tmp_path):
    config_path = tmp_path / "detector_config.json"
    config_path.write_text(
        json.dumps(
            {
                "config_type": "anomaly_detector",
                "anomaly_detector": {
                    "behavior_score_threshold": 1.5,
                    "anomalous_score_threshold": 5.0,
                    "short_session_median_ratio": 0.45,
                    "low_mean_rt_median_ratio": 0.45,
                    "low_rt_iqr_median_ratio": 0.4,
                    "low_section_variance_median_ratio": 0.2,
                    "moderate_back_nav_rate_threshold": 0.3,
                    "long_pause_median_ratio": 2.5,
                },
            }
        ),
        encoding="utf-8",
    )

    loaded = load_detector_config(config_path)

    assert loaded["behavior_score_threshold"] == pytest.approx(1.5)
    assert loaded["anomalous_score_threshold"] == pytest.approx(5.0)
    assert loaded["short_session_median_ratio"] == pytest.approx(0.45)
    assert loaded["low_mean_rt_median_ratio"] == pytest.approx(0.45)
    assert loaded["low_rt_iqr_median_ratio"] == pytest.approx(0.4)
    assert loaded["low_section_variance_median_ratio"] == pytest.approx(0.2)
    assert loaded["moderate_back_nav_rate_threshold"] == pytest.approx(0.3)
    assert loaded["long_pause_median_ratio"] == pytest.approx(2.5)


def test_build_detector_config_from_args_merges_file_and_cli_overrides(tmp_path):
    config_path = tmp_path / "detector_config.json"
    config_path.write_text(
        json.dumps(
            {
                "anomaly_detector": {
                    "behavior_score_threshold": 1.5,
                    "anomalous_score_threshold": 5.0,
                }
            }
        ),
        encoding="utf-8",
    )

    args = Namespace(
        detector_config=str(config_path),
        behavior_threshold=2.5,
        anomalous_threshold=5.5,
    )

    merged = build_detector_config_from_args(args)

    assert merged["behavior_score_threshold"] == pytest.approx(2.5)
    assert merged["anomalous_score_threshold"] == pytest.approx(5.5)


def test_stress_dataset_records_difficulty_in_summary(tmp_path):
    generated = build_dataset(
        dataset_size=12,
        seed=7,
        anomaly_ratio=0.25,
        output_dir=tmp_path / "stress_dataset",
        difficulty="stress",
    )

    summary = json.loads((tmp_path / "stress_dataset" / "dataset_summary.json").read_text())
    assert summary["difficulty"] == "stress"
    assert Path(generated["surveycto_path"]).exists()
    assert Path(generated["odk_path"]).exists()
    assert Path(generated["ground_truth_path"]).exists()
