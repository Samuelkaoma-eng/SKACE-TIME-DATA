from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.features.section_features import SectionFeatureExtractor
from src.parsers.odk_parser import ODKParser
from src.parsers.surveycto_parser import SurveyCTOParser
from src.pipeline.controller import PipelineController
from src.validation.reporting import (
    anomaly_report_view,
    compute_binary_metrics,
    feature_dataset_view,
    load_ground_truth,
    merge_ground_truth,
    sanitize_label,
    save_evaluation_artifacts,
)


FORMAT_CONFIG = {
    "surveycto": {
        "raw_path": Path("data/synthetic_datasets/n500/audit_logs_surveycto.csv"),
        "scale_path": Path("data/synthetic_datasets/n10000/audit_logs_surveycto.csv"),
        "ground_truth": Path("data/synthetic_datasets/n500/ground_truth_labels.csv"),
        "required_columns": ["interview_id", "node", "event", "start", "end", "duration_ms"],
        "timestamp_kind": "epoch_ms",
        "timestamp_column": "start",
        "parser": SurveyCTOParser(),
    },
    "odk": {
        "raw_path": Path("data/synthetic_datasets/n500/audit_logs_odk.csv"),
        "scale_path": Path("data/synthetic_datasets/n10000/audit_logs_odk.csv"),
        "ground_truth": Path("data/synthetic_datasets/n500/ground_truth_labels.csv"),
        "required_columns": ["instance_id", "name", "event", "start_time", "end_time"],
        "timestamp_kind": "iso8601",
        "timestamp_column": "start_time",
        "parser": ODKParser(),
    },
}

WEIGHTS = {
    "flag_too_fast": 3,
    "flag_too_slow": 2,
    "flag_low_entropy": 2,
    "flag_uniform_timing": 2,
    "flag_high_back_nav": 1,
    "flag_iqr_duration": 2,
    "flag_iqr_rt_mean": 2,
    "flag_iqr_entropy": 1,
    "flag_rule_pause": 1,
    "flag_invalid_ratio": 3,
}


@dataclass
class CheckResult:
    step: str
    passed: bool
    details: str


def assert_required_columns(df: pd.DataFrame, required_columns: list[str]) -> tuple[bool, str]:
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        return False, f"Missing required columns: {missing}"
    return True, f"Required columns present: {required_columns}"


def check_timestamp_kind(series: pd.Series, kind: str) -> tuple[bool, str]:
    values = series.dropna().astype(str).head(10).tolist()
    if not values:
        return False, "No non-null timestamp values available"

    if kind == "epoch_ms":
        okay = all(value.isdigit() and len(value) >= 13 for value in values)
        return okay, f"Sample timestamps: {values[:3]}"

    parsed = pd.to_datetime(values, errors="coerce", utc=True)
    okay = parsed.notna().all()
    return okay, f"Sample timestamps: {values[:3]}"


def run_pipeline(
    raw_files: list[Path],
    output_dir: Path,
    label: str,
    reuse_if_present: bool = False,
) -> tuple[pd.DataFrame, dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    pipeline_output_path = output_dir / f"pipeline_output_{label}.csv"
    if reuse_if_present and pipeline_output_path.exists():
        predictions = pd.read_csv(pipeline_output_path)
        return predictions, {"runtime_seconds": math.nan}

    controller = PipelineController(parser_type="auto")
    started = time.time()
    predictions = controller.process_batch(raw_files)
    runtime_seconds = round(time.time() - started, 2)
    if predictions.empty:
        raise ValueError(f"Pipeline returned no rows for {raw_files}")

    feature_dataset = feature_dataset_view(predictions)
    anomaly_report = anomaly_report_view(predictions)
    feature_dataset.to_csv(output_dir / f"feature_dataset_{label}.csv", index=False)
    anomaly_report.to_csv(output_dir / f"anomaly_report_{label}.csv", index=False)
    predictions.to_csv(pipeline_output_path, index=False)
    return predictions, {"runtime_seconds": runtime_seconds}


def manual_question_response_times(interview_cir: pd.DataFrame) -> dict[str, float]:
    valid_cir = interview_cir[
        (~interview_cir["field_name"].isin(["unknown_field", "MainSection"]))
        & (~interview_cir["event_type"].isin(["form_start", "form_end"]))
    ].copy()
    response_times: dict[str, float] = {}

    for field_name, group in valid_cir.groupby("field_name"):
        group = group.sort_values("start_ms")
        nav_mask = group["event_type"].str.contains("jump|back|backward|forward|skip", case=False, na=False)
        question_events = group[~nav_mask]
        window = question_events if not question_events.empty else group
        if window.empty:
            response_times[field_name] = 0.0
            continue
        response_times[field_name] = float(window["end_ms"].max() - window["start_ms"].min())
    return response_times


def manual_t02_iqr(q_response_times: dict[str, float]) -> float:
    values = np.array([value for value in q_response_times.values() if value > 0], dtype=float)
    if len(values) == 0:
        return 0.0
    q75, q25 = np.percentile(values, [75, 25])
    return float(q75 - q25)


def reconstruct_anomaly_score(row: pd.Series) -> int:
    return int(sum(int(row.get(flag, 0)) * weight for flag, weight in WEIGHTS.items()))


def expected_status(row: pd.Series) -> str:
    if int(row.get("is_data_quality_issue", 0)) == 1 or int(row.get("anomaly_score", 0)) >= 5:
        return "FLAGGED"
    if int(row.get("anomaly_score", 0)) >= 3:
        return "REVIEW"
    return "CLEAN"


def duration_iqr_baseline_metrics(predictions: pd.DataFrame, ground_truth: pd.DataFrame) -> dict:
    baseline = predictions[["interview_id", "V-01_total_interview_duration_ms"]].copy()
    durations = baseline["V-01_total_interview_duration_ms"]
    q1, q3 = durations.quantile(0.25), durations.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    baseline["is_anomalous_behavior"] = (
        (durations < lower) | (durations > upper)
    ).astype(int)
    baseline["anomaly_category"] = np.where(
        baseline["is_anomalous_behavior"].astype(bool), "anomalous", "normal"
    )
    merged = merge_ground_truth(ground_truth, baseline)
    return compute_binary_metrics(merged)


def zero_back_nav_baseline_metrics(predictions: pd.DataFrame, ground_truth: pd.DataFrame) -> dict:
    baseline = predictions[["interview_id", "V-10_zero_back_nav_flag"]].copy()
    baseline["is_anomalous_behavior"] = baseline["V-10_zero_back_nav_flag"].fillna(0).astype(int)
    baseline["anomaly_category"] = np.where(
        baseline["is_anomalous_behavior"].astype(bool), "anomalous", "normal"
    )
    merged = merge_ground_truth(ground_truth, baseline)
    return compute_binary_metrics(merged)


def fabricated_profile_summary(predictions: pd.DataFrame, ground_truth: pd.DataFrame) -> pd.DataFrame:
    merged = ground_truth.merge(predictions, on="interview_id", how="inner", validate="one_to_one")
    rows = []
    for anomaly_type in ["normal", "fabricated"]:
        subset = merged[merged["anomaly_type"].astype(str).str.lower() == anomaly_type]
        rows.append(
            {
                "anomaly_type": anomaly_type,
                "count": int(len(subset)),
                "mean_rt_variance": float(subset["T-01_rt_variance"].mean()) if len(subset) else math.nan,
                "mean_rt_iqr": float(subset["T-02_rt_iqr"].mean()) if len(subset) else math.nan,
                "mean_rt_entropy": float(subset["T-03_rt_entropy"].mean()) if len(subset) else math.nan,
                "mean_back_nav_count": float(subset["V-06_back_navigation_total_count"].mean()) if len(subset) else math.nan,
                "mean_total_duration_ms": float(subset["V-01_total_interview_duration_ms"].mean()) if len(subset) else math.nan,
            }
        )
    return pd.DataFrame(rows)


def run_examiner_audit(output_dir: Path) -> tuple[list[CheckResult], dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    checks: list[CheckResult] = []
    summary: dict = {"datasets": {}, "scale": {}}

    predictions_by_format: dict[str, pd.DataFrame] = {}
    metrics_by_format: dict[str, dict] = {}

    for fmt, config in FORMAT_CONFIG.items():
        raw_path = config["raw_path"]
        raw_df = pd.read_csv(raw_path)
        ok, detail = assert_required_columns(raw_df, config["required_columns"])
        checks.append(CheckResult(f"{fmt}: raw required columns", ok, detail))

        ts_ok, ts_detail = check_timestamp_kind(raw_df[config["timestamp_column"]], config["timestamp_kind"])
        checks.append(CheckResult(f"{fmt}: timestamp format", ts_ok, ts_detail))

        cir = config["parser"].parse(raw_path)
        cir_ok = list(cir.columns) == ["interview_id", "field_name", "event_type", "start_ms", "end_ms", "duration_ms"]
        checks.append(CheckResult(f"{fmt}: CIR schema", cir_ok, f"CIR columns: {list(cir.columns)}"))

        first_timed = cir[cir["start_ms"].notna() & cir["end_ms"].notna()].iloc[0]
        duration_ok = pd.isna(first_timed["duration_ms"]) or abs(
            float(first_timed["duration_ms"]) - float(first_timed["end_ms"] - first_timed["start_ms"])
        ) < 1e-6
        checks.append(
            CheckResult(
                f"{fmt}: CIR duration consistency",
                duration_ok,
                (
                    f"interview_id={first_timed['interview_id']} field={first_timed['field_name']} "
                    f"duration_ms={first_timed['duration_ms']}"
                ),
            )
        )

        run_dir = output_dir / fmt
        label = sanitize_label(f"examiner_n500_{fmt}")
        predictions, runtime_meta = run_pipeline(
            [raw_path],
            run_dir,
            label,
            reuse_if_present=False,
        )
        predictions_by_format[fmt] = predictions

        ground_truth = load_ground_truth(config["ground_truth"])
        merged = merge_ground_truth(ground_truth, predictions)
        metrics = compute_binary_metrics(merged)
        metrics_by_format[fmt] = metrics
        save_evaluation_artifacts(metrics, merged, run_dir, label)

        summary["datasets"][fmt] = {
            "metrics": metrics,
            "runtime_seconds": runtime_meta["runtime_seconds"],
        }

        if fmt == "surveycto":
            interview_id = str(predictions.iloc[0]["interview_id"])
            interview_cir = cir[cir["interview_id"].astype(str) == interview_id].copy()
            q_times = manual_question_response_times(interview_cir)
            chosen_field = sorted(q_times)[0]
            row = predictions[predictions["interview_id"].astype(str) == interview_id].iloc[0]

            q01_ok = abs(float(row["Q-01_response_time_ms"]) - float(np.mean(list(q_times.values())))) < 1e-6
            checks.append(
                CheckResult(
                    "surveycto: manual Q-01 aggregate check",
                    q01_ok,
                    f"interview={interview_id} field_count={len(q_times)} chosen_field={chosen_field}",
                )
            )

            manual_v01 = float(interview_cir["end_ms"].max() - interview_cir["start_ms"].min())
            v01_ok = abs(float(row["V-01_total_interview_duration_ms"]) - manual_v01) < 1e-6
            checks.append(CheckResult("surveycto: manual V-01 check", v01_ok, f"manual={manual_v01} pipeline={row['V-01_total_interview_duration_ms']}"))

            manual_t02 = manual_t02_iqr(q_times)
            t02_ok = abs(float(row["T-02_rt_iqr"]) - manual_t02) < 1e-6
            checks.append(CheckResult("surveycto: manual T-02 check", t02_ok, f"manual={manual_t02} pipeline={row['T-02_rt_iqr']}"))

            score_ok = reconstruct_anomaly_score(row) == int(row["anomaly_score"])
            checks.append(CheckResult("surveycto: anomaly score reconstruction", score_ok, f"expected={reconstruct_anomaly_score(row)} actual={row['anomaly_score']}"))

            status_ok = expected_status(row) == str(row["status"])
            checks.append(CheckResult("surveycto: status mapping", status_ok, f"expected={expected_status(row)} actual={row['status']}"))

            fabricated_summary = fabricated_profile_summary(predictions, ground_truth)
            fabricated_row = fabricated_summary[fabricated_summary["anomaly_type"] == "fabricated"].iloc[0]
            normal_row = fabricated_summary[fabricated_summary["anomaly_type"] == "normal"].iloc[0]
            fabricated_distinct = (
                fabricated_row["mean_rt_variance"] < normal_row["mean_rt_variance"]
                and fabricated_row["mean_rt_iqr"] < normal_row["mean_rt_iqr"]
                and fabricated_row["mean_rt_entropy"] < normal_row["mean_rt_entropy"]
                and fabricated_row["mean_back_nav_count"] < normal_row["mean_back_nav_count"]
                and fabricated_row["mean_total_duration_ms"] < normal_row["mean_total_duration_ms"]
            )
            checks.append(
                CheckResult(
                    "surveycto: fabricated vs normal signature separation",
                    bool(fabricated_distinct),
                    fabricated_summary.to_string(index=False),
                )
            )
            fabricated_summary.to_csv(run_dir / "fabricated_profile_summary.csv", index=False)

            baseline_duration = duration_iqr_baseline_metrics(predictions, ground_truth)
            baseline_zero_nav = zero_back_nav_baseline_metrics(predictions, ground_truth)
            summary["datasets"][fmt]["baseline_duration_iqr"] = baseline_duration
            summary["datasets"][fmt]["baseline_zero_back_nav"] = baseline_zero_nav

    parity_ok = (
        abs(metrics_by_format["surveycto"]["precision"] - metrics_by_format["odk"]["precision"]) <= 0.05
        and abs(metrics_by_format["surveycto"]["recall"] - metrics_by_format["odk"]["recall"]) <= 0.05
    )
    checks.append(
        CheckResult(
            "cross-format parity",
            parity_ok,
            (
                f"surveycto precision/recall={metrics_by_format['surveycto']['precision']:.4f}/"
                f"{metrics_by_format['surveycto']['recall']:.4f}, "
                f"odk precision/recall={metrics_by_format['odk']['precision']:.4f}/"
                f"{metrics_by_format['odk']['recall']:.4f}"
            ),
        )
    )

    # Scale test: compare n500 vs n10000 SurveyCTO performance and runtime.
    scale_dir = output_dir / "scale"
    n500_predictions, n500_runtime = run_pipeline(
        [FORMAT_CONFIG["surveycto"]["raw_path"]],
        scale_dir,
        "scale_n500_surveycto",
        reuse_if_present=False,
    )
    n10000_predictions, n10000_runtime = run_pipeline(
        [FORMAT_CONFIG["surveycto"]["scale_path"]],
        scale_dir,
        "scale_n10000_surveycto",
        reuse_if_present=False,
    )
    n500_gt = load_ground_truth(FORMAT_CONFIG["surveycto"]["ground_truth"])
    n10000_gt = load_ground_truth(Path("data/synthetic_datasets/n10000/ground_truth_labels.csv"))
    n500_merged = merge_ground_truth(n500_gt, n500_predictions)
    n10000_merged = merge_ground_truth(n10000_gt, n10000_predictions)
    n500_metrics = compute_binary_metrics(n500_merged)
    n10000_metrics = compute_binary_metrics(n10000_merged)
    runtime_ratio = (
        n10000_runtime["runtime_seconds"] / n500_runtime["runtime_seconds"]
        if n500_runtime["runtime_seconds"] > 0
        else math.inf
    )
    precision_delta = abs(n10000_metrics["precision"] - n500_metrics["precision"])
    recall_delta = abs(n10000_metrics["recall"] - n500_metrics["recall"])
    scale_ok = precision_delta <= 0.05 and recall_delta <= 0.05
    checks.append(
        CheckResult(
            "scale stability (n500 vs n10000 surveycto)",
            scale_ok,
            (
                f"runtime_ratio={runtime_ratio:.2f}, "
                f"n500 precision/recall={n500_metrics['precision']:.4f}/{n500_metrics['recall']:.4f}, "
                f"n10000 precision/recall={n10000_metrics['precision']:.4f}/{n10000_metrics['recall']:.4f}"
            ),
        )
    )
    summary["scale"] = {
        "n500_runtime_seconds": n500_runtime["runtime_seconds"],
        "n10000_runtime_seconds": n10000_runtime["runtime_seconds"],
        "runtime_ratio": runtime_ratio,
        "n500_metrics": n500_metrics,
        "n10000_metrics": n10000_metrics,
    }

    return checks, summary


def write_report(checks: list[CheckResult], summary: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / "strict_examiner_audit_report.md"
    json_path = output_dir / "strict_examiner_audit_report.json"
    summary_df = pd.DataFrame([vars(check) for check in checks])

    def json_default(value):
        if isinstance(value, (np.bool_,)):
            return bool(value)
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating,)):
            return float(value)
        if isinstance(value, Path):
            return str(value)
        raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")

    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "checks": [vars(check) for check in checks],
                "summary": summary,
            },
            handle,
            indent=2,
            default=json_default,
        )

    with md_path.open("w", encoding="utf-8") as handle:
        handle.write("# Strict Examiner Audit Report\n\n")
        handle.write("## Checklist Results\n\n```text\n")
        handle.write(summary_df.to_string(index=False))
        handle.write("\n```\n")
        handle.write("\n## Metrics Summary\n\n```text\n")
        handle.write(json.dumps(summary, indent=2))
        handle.write("\n```\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an examiner-style reproducibility audit across data, features, anomaly reports, and metrics.")
    parser.add_argument("--output-dir", default="output/examiner_audit", help="Where audit artifacts should be written.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    checks, summary = run_examiner_audit(output_dir)
    write_report(checks, summary, output_dir)

    df = pd.DataFrame([vars(check) for check in checks])
    print("\nStrict examiner audit results")
    print(df.to_string(index=False))
    return 0 if df["passed"].all() else 1


if __name__ == "__main__":
    raise SystemExit(main())
