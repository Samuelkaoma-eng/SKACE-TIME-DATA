from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score


ANOMALY_FLAG_COLUMNS = [
    "flag_invalid_ratio",
    "flag_missing_data",
    "flag_inconsistent_metrics",
    "flag_too_fast",
    "flag_too_slow",
    "flag_zero_back_nav",
    "flag_low_entropy",
    "flag_uniform_timing",
    "flag_rule_pause",
    "flag_iqr_duration",
    "flag_iqr_rt_mean",
    "flag_iqr_entropy",
    "flag_iqr_variance",
    "flag_high_back_nav",
]

ANOMALY_OUTPUT_COLUMNS = [
    "file_name",
    "interview_id",
    "anomaly_score",
    "anomaly_category",
    "is_data_quality_issue",
    "is_anomalous_behavior",
    "is_anomalous",
    "iqr_flags",
    "rule_flags",
    "flagged_features",
    "status",
]

FEATURE_DATASET_EXCLUDE_COLUMNS = ANOMALY_FLAG_COLUMNS + ANOMALY_OUTPUT_COLUMNS

DEFAULT_PRECISION_THRESHOLD = 0.80
DEFAULT_RECALL_THRESHOLD = 0.75
DEFAULT_FABRICATED_SCORE_THRESHOLD = 5
DEFAULT_NORMAL_SCORE_MAX = 1


def sanitize_label(label: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in str(label))
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "run"


def feature_dataset_view(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=[col for col in FEATURE_DATASET_EXCLUDE_COLUMNS if col in df.columns]).copy()


def anomaly_report_view(df: pd.DataFrame) -> pd.DataFrame:
    available_cols = [col for col in ANOMALY_OUTPUT_COLUMNS if col in df.columns]
    return df[available_cols].copy()


def load_ground_truth(ground_truth_path: str | Path) -> pd.DataFrame:
    path = Path(ground_truth_path)
    ground_truth = pd.read_csv(path)
    rename_map = {}
    if "is_anomalous" not in ground_truth.columns:
        for candidate in ("is_anomalous_ground_truth", "ground_truth_is_anomalous"):
            if candidate in ground_truth.columns:
                rename_map[candidate] = "is_anomalous"
                break
    if rename_map:
        ground_truth = ground_truth.rename(columns=rename_map)

    required = {"interview_id", "is_anomalous"}
    missing = required - set(ground_truth.columns)
    if missing:
        raise ValueError(f"Ground truth file is missing columns {sorted(missing)}: {path}")

    ground_truth = ground_truth.copy()
    ground_truth["interview_id"] = ground_truth["interview_id"].astype(str)
    ground_truth["is_anomalous"] = ground_truth["is_anomalous"].astype(int)
    return ground_truth


def merge_ground_truth(ground_truth: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    pred_cols = [
        "interview_id",
        "anomaly_category",
        "anomaly_score",
        "is_data_quality_issue",
        "is_anomalous",
        "is_anomalous_behavior",
        "iqr_flags",
        "rule_flags",
        "flagged_features",
        "status",
    ]
    available_cols = [col for col in pred_cols if col in predictions.columns]
    pred = predictions[available_cols].copy()
    if "interview_id" not in pred.columns:
        raise ValueError("Predictions are missing interview_id")

    pred["interview_id"] = pred["interview_id"].astype(str)
    rename_map = {}
    if "is_anomalous" in pred.columns:
        rename_map["is_anomalous"] = "predicted_is_anomalous"
    if "is_anomalous_behavior" in pred.columns:
        rename_map["is_anomalous_behavior"] = "predicted_is_anomalous_behavior"
    if rename_map:
        pred = pred.rename(columns=rename_map)

    if pred["interview_id"].duplicated().any():
        dupes = pred.loc[pred["interview_id"].duplicated(), "interview_id"].unique().tolist()
        raise ValueError(f"Predictions contain duplicate interview IDs: {dupes[:10]}")

    merged = ground_truth.merge(pred, on="interview_id", how="inner", validate="one_to_one")
    if merged.empty:
        raise ValueError("No prediction rows matched the ground truth interview IDs")
    if len(merged) != len(ground_truth):
        matched_ids = set(merged["interview_id"].astype(str))
        missing_ids = ground_truth.loc[~ground_truth["interview_id"].astype(str).isin(matched_ids), "interview_id"].tolist()
        raise ValueError(
            f"Predictions matched {len(merged)} of {len(ground_truth)} ground-truth rows. "
            f"Missing IDs include: {missing_ids[:10]}"
        )
    return merged


def _predicted_binary_series(merged: pd.DataFrame) -> pd.Series:
    if "predicted_is_anomalous_behavior" in merged.columns:
        return merged["predicted_is_anomalous_behavior"].astype(int)
    if "predicted_is_anomalous" in merged.columns:
        return merged["predicted_is_anomalous"].astype(int)
    raise ValueError("Predictions are missing both predicted_is_anomalous_behavior and predicted_is_anomalous")


def compute_contract_checks(
    merged: pd.DataFrame,
    metrics: dict,
    precision_threshold: float = DEFAULT_PRECISION_THRESHOLD,
    recall_threshold: float = DEFAULT_RECALL_THRESHOLD,
    fabricated_score_threshold: int = DEFAULT_FABRICATED_SCORE_THRESHOLD,
    normal_score_max: int = DEFAULT_NORMAL_SCORE_MAX,
) -> dict:
    contract = {
        "precision_threshold": float(precision_threshold),
        "recall_threshold": float(recall_threshold),
        "fabricated_score_threshold": int(fabricated_score_threshold),
        "normal_score_max": int(normal_score_max),
        "passes_precision_threshold": bool(metrics["precision"] >= precision_threshold),
        "passes_recall_threshold": bool(metrics["recall"] >= recall_threshold),
    }

    if "anomaly_score" in merged.columns:
        if "anomaly_type" in merged.columns:
            anomaly_type = merged["anomaly_type"].astype(str).str.lower()
            fabricated = merged[anomaly_type == "fabricated"]
            normal = merged[anomaly_type == "normal"]
        else:
            fabricated = merged.iloc[0:0].copy()
            normal = merged[merged["is_anomalous"].astype(int) == 0]

        contract["fabricated_total"] = int(len(fabricated))
        contract["fabricated_score_ge_threshold"] = (
            int((fabricated["anomaly_score"] >= fabricated_score_threshold).sum()) if len(fabricated) else 0
        )
        contract["normal_total"] = int(len(normal))
        contract["normal_score_le_threshold"] = int((normal["anomaly_score"] <= normal_score_max).sum()) if len(normal) else 0
        contract["passes_fabricated_score_threshold"] = bool(
            len(fabricated) == 0 or contract["fabricated_score_ge_threshold"] == len(fabricated)
        )
        contract["passes_normal_score_threshold"] = bool(
            len(normal) == 0 or contract["normal_score_le_threshold"] == len(normal)
        )
    else:
        contract["fabricated_total"] = 0
        contract["fabricated_score_ge_threshold"] = 0
        contract["normal_total"] = int((merged["is_anomalous"].astype(int) == 0).sum())
        contract["normal_score_le_threshold"] = 0
        contract["passes_fabricated_score_threshold"] = False
        contract["passes_normal_score_threshold"] = False

    contract["passes_overall_contract"] = bool(
        contract["passes_precision_threshold"]
        and contract["passes_recall_threshold"]
        and contract["passes_fabricated_score_threshold"]
        and contract["passes_normal_score_threshold"]
    )
    return contract


def compute_binary_metrics(
    merged: pd.DataFrame,
    precision_threshold: float = DEFAULT_PRECISION_THRESHOLD,
    recall_threshold: float = DEFAULT_RECALL_THRESHOLD,
    fabricated_score_threshold: int = DEFAULT_FABRICATED_SCORE_THRESHOLD,
    normal_score_max: int = DEFAULT_NORMAL_SCORE_MAX,
) -> dict:
    y_true = merged["is_anomalous"].astype(int)
    y_pred = _predicted_binary_series(merged)

    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    accuracy = accuracy_score(y_true, y_pred)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    metrics = {
        "total_samples": int(len(merged)),
        "true_positive": int(tp),
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "accuracy": float(accuracy),
        "specificity": float(tn / (tn + fp)) if (tn + fp) else 0.0,
        "anomalies_true": int(y_true.sum()),
        "anomalies_predicted": int(y_pred.sum()),
        "normals_true": int((y_true == 0).sum()),
        "normals_predicted": int((y_pred == 0).sum()),
    }
    metrics.update(
        compute_contract_checks(
            merged,
            metrics,
            precision_threshold=precision_threshold,
            recall_threshold=recall_threshold,
            fabricated_score_threshold=fabricated_score_threshold,
            normal_score_max=normal_score_max,
        )
    )
    return metrics


def compute_detection_by_type(merged: pd.DataFrame) -> list[dict]:
    if "anomaly_type" not in merged.columns:
        return []

    rows = []
    y_pred = _predicted_binary_series(merged)
    enriched = merged.copy()
    enriched["_predicted_binary"] = y_pred
    anomalous = enriched[enriched["is_anomalous"].astype(int) == 1]
    for anomaly_type, group in anomalous.groupby("anomaly_type"):
        detected = int(group["_predicted_binary"].sum())
        rows.append(
            {
                "anomaly_type": str(anomaly_type),
                "total": int(len(group)),
                "detected": detected,
                "detection_rate": float(detected / len(group)) if len(group) else 0.0,
            }
        )
    return rows


def save_evaluation_artifacts(
    metrics_rows: dict | Iterable[dict],
    merged: pd.DataFrame,
    output_dir: str | Path,
    prefix: str,
    detection_rows: Iterable[dict] | None = None,
) -> dict:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_prefix = sanitize_label(prefix)

    metrics_df = pd.DataFrame(metrics_rows if isinstance(metrics_rows, list) else [metrics_rows])
    metrics_csv = out_dir / f"metrics_{safe_prefix}.csv"
    metrics_json = out_dir / f"metrics_{safe_prefix}.json"
    metrics_md = out_dir / f"metrics_{safe_prefix}.md"
    predictions_csv = out_dir / f"predictions_{safe_prefix}.csv"

    metrics_df.to_csv(metrics_csv, index=False)
    with metrics_json.open("w", encoding="utf-8") as handle:
        json.dump(metrics_df.to_dict(orient="records"), handle, indent=2)
    merged.to_csv(predictions_csv, index=False)

    detection_path = None
    detection_rows = list(detection_rows or [])
    if detection_rows:
        detection_df = pd.DataFrame(detection_rows)
        detection_path = out_dir / f"detection_by_type_{safe_prefix}.csv"
        detection_df.to_csv(detection_path, index=False)
    else:
        detection_df = pd.DataFrame()

    with metrics_md.open("w", encoding="utf-8") as handle:
        handle.write(f"# Metrics: {safe_prefix}\n\n")
        handle.write("## Summary\n\n```text\n")
        handle.write(metrics_df.to_string(index=False))
        handle.write("\n```\n")
        if not detection_df.empty:
            handle.write("\n## Detection By Type\n\n```text\n")
            handle.write(detection_df.to_string(index=False))
            handle.write("\n```\n")

    return {
        "metrics_csv": str(metrics_csv),
        "metrics_json": str(metrics_json),
        "metrics_md": str(metrics_md),
        "predictions_csv": str(predictions_csv),
        "detection_csv": str(detection_path) if detection_path else None,
    }
