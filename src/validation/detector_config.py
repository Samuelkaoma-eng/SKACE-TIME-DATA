from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.validation.anomaly_detector import AnomalyDetector


DETECTOR_CONFIG_KEYS = [
    "uniform_timing_cv",
    "behavior_score_threshold",
    "anomalous_score_threshold",
    "too_fast_ms",
    "too_slow_ms",
    "low_entropy_threshold",
    "low_variance_threshold",
    "short_session_median_ratio",
    "low_mean_rt_median_ratio",
    "low_rt_iqr_median_ratio",
    "low_section_variance_median_ratio",
    "moderate_back_nav_rate_threshold",
    "long_pause_median_ratio",
    "high_back_nav_rate_threshold",
    "rule_pause_count_min",
    "rule_pause_min_ms",
    "elevated_pause_median_ratio",
]


def default_detector_config() -> dict:
    detector = AnomalyDetector()
    return {key: getattr(detector, key) for key in DETECTOR_CONFIG_KEYS}


def filter_detector_config(raw_config: dict | None) -> dict:
    if not raw_config:
        return {}
    return {key: raw_config[key] for key in DETECTOR_CONFIG_KEYS if key in raw_config}


def validate_detector_config(detector_config: dict) -> dict:
    config = filter_detector_config(detector_config)
    behavior = config.get("behavior_score_threshold")
    anomalous = config.get("anomalous_score_threshold")
    if behavior is not None and anomalous is not None and anomalous < behavior:
        raise ValueError(
            "anomalous_score_threshold must be greater than or equal to behavior_score_threshold"
        )
    return config


def load_detector_config(path: str | Path) -> dict:
    config_path = Path(path)
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Detector config must be a JSON object: {config_path}")

    candidate = payload.get("anomaly_detector", payload)
    if not isinstance(candidate, dict):
        raise ValueError(f"Detector config payload is invalid: {config_path}")

    config = validate_detector_config(candidate)
    if not config:
        raise ValueError(f"Detector config did not contain any supported detector keys: {config_path}")
    return config


def build_recalibrated_detector_config(
    behavior_score_threshold: float,
    data_paths: list[str],
    ground_truth_path: str,
    base_config: dict | None = None,
) -> dict:
    detector_config = default_detector_config()
    detector_config.update(filter_detector_config(base_config))
    detector_config["behavior_score_threshold"] = float(behavior_score_threshold)
    detector_config["anomalous_score_threshold"] = max(
        float(detector_config["anomalous_score_threshold"]),
        float(behavior_score_threshold),
    )
    detector_config = validate_detector_config(detector_config)

    return {
        "config_type": "anomaly_detector",
        "generated_by": "threshold_recalibration.py",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "calibration_target": "behavior_score_threshold",
        "notes": (
            "This config applies the recalibrated behavior_score_threshold directly. "
            "The anomalous_score_threshold is kept at least as high as the behavior threshold "
            "to preserve category ordering."
        ),
        "data_paths": list(data_paths),
        "ground_truth": str(ground_truth_path),
        "anomaly_detector": detector_config,
    }
