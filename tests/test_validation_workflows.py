import json
from argparse import Namespace

import pandas as pd
import pytest

from feature_validation import cohens_d, compute_feature_stats
from run_pipeline import build_detector_config_from_args
from src.validation.detector_config import (
    build_recalibrated_detector_config,
    load_detector_config,
)


def test_compute_feature_stats_reports_cohens_d():
    eval_df = pd.DataFrame(
        {
            "interview_id": [f"INT{i}" for i in range(8)],
            "ground_truth_is_anomalous": [0, 0, 0, 0, 1, 1, 1, 1],
            "demo_feature": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
        }
    )

    stats_df = compute_feature_stats(eval_df, alpha=0.05)

    assert "cohens_d" in stats_df.columns
    assert "rank_biserial_effect_size" in stats_df.columns
    assert "effect_size_method" in stats_df.columns

    row = stats_df.loc[stats_df["feature"] == "demo_feature"].iloc[0]
    expected_d = cohens_d(
        eval_df.loc[eval_df["ground_truth_is_anomalous"] == 0, "demo_feature"],
        eval_df.loc[eval_df["ground_truth_is_anomalous"] == 1, "demo_feature"],
    )
    assert row["effect_size_method"] == "cohens_d"
    assert row["effect_size"] == pytest.approx(expected_d)
    assert row["cohens_d"] == pytest.approx(expected_d)
    assert row["abs_cohens_d"] == pytest.approx(abs(expected_d))


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


def test_load_detector_config_reads_threshold_file(tmp_path):
    config_path = tmp_path / "detector_config.json"
    config_path.write_text(
        json.dumps(
            {
                "config_type": "anomaly_detector",
                "anomaly_detector": {
                    "behavior_score_threshold": 1.5,
                    "anomalous_score_threshold": 4.0,
                },
            }
        ),
        encoding="utf-8",
    )

    loaded = load_detector_config(config_path)

    assert loaded["behavior_score_threshold"] == pytest.approx(1.5)
    assert loaded["anomalous_score_threshold"] == pytest.approx(4.0)


def test_build_detector_config_from_args_merges_file_and_cli_overrides(tmp_path):
    config_path = tmp_path / "detector_config.json"
    config_path.write_text(
        json.dumps(
            {
                "anomaly_detector": {
                    "behavior_score_threshold": 1.5,
                    "anomalous_score_threshold": 4.0,
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

