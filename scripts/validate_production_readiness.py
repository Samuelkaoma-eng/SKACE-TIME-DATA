import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline.controller import PipelineController
from src.validation.detector_config import load_detector_config
from src.validation.reporting import (
    anomaly_report_view,
    compute_binary_metrics,
    compute_detection_by_type,
    feature_dataset_view,
    load_ground_truth,
    merge_ground_truth,
    sanitize_label,
    save_evaluation_artifacts,
)
from tests.generate_benchmark_datasets import build_dataset


FORMAT_TO_FILENAME = {
    "surveycto": "audit_logs_surveycto.csv",
    "odk": "audit_logs_odk.csv",
}


def evaluate_file(
    raw_file: Path,
    ground_truth_path: Path,
    parser_type: str,
    output_dir: Path,
    prefix: str,
    detector_config: dict | None = None,
) -> dict:
    controller = PipelineController(parser_type=parser_type, detector_config=detector_config)
    started = time.time()
    predictions = controller.process_batch([raw_file])
    runtime_seconds = round(time.time() - started, 2)

    if predictions.empty:
        raise ValueError(f"Pipeline returned no rows for {raw_file}")

    feature_dataset = feature_dataset_view(predictions)
    anomaly_report = anomaly_report_view(predictions)

    output_dir.mkdir(parents=True, exist_ok=True)
    feature_dataset.to_csv(output_dir / f"feature_dataset_{prefix}.csv", index=False)
    anomaly_report.to_csv(output_dir / f"anomaly_report_{prefix}.csv", index=False)
    predictions.to_csv(output_dir / f"pipeline_output_{prefix}.csv", index=False)

    ground_truth = load_ground_truth(ground_truth_path)
    merged = merge_ground_truth(ground_truth, predictions)
    metrics = compute_binary_metrics(merged)
    detection_rows = compute_detection_by_type(merged)
    save_evaluation_artifacts(metrics, merged, output_dir, prefix, detection_rows)

    metrics.update(
        {
            "runtime_seconds": runtime_seconds,
            "rows_returned": int(len(predictions)),
            "raw_file": str(raw_file),
        }
    )
    return metrics


def write_summary(summary_df: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "production_readiness_summary.csv"
    json_path = output_dir / "production_readiness_summary.json"
    md_path = output_dir / "production_readiness_summary.md"

    summary_df.to_csv(csv_path, index=False)
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(summary_df.to_dict(orient="records"), handle, indent=2)

    overall_ready = bool(summary_df["passes_overall_contract"].all()) if not summary_df.empty else False
    metric_ready = (
        bool((summary_df["passes_precision_threshold"] & summary_df["passes_recall_threshold"]).all())
        if not summary_df.empty
        else False
    )
    score_contract_ready = (
        bool(
            (
                summary_df["passes_fabricated_score_threshold"]
                & summary_df["passes_normal_score_threshold"]
            ).all()
        )
        if not summary_df.empty
        else False
    )
    difficulty_values = set(summary_df.get("difficulty", pd.Series(dtype=str)).dropna().astype(str))
    is_stress_run = difficulty_values == {"stress"}

    with md_path.open("w", encoding="utf-8") as handle:
        title = "Stress Robustness Validation" if is_stress_run else "Production Readiness Validation"
        handle.write(f"# {title}\n\n")
        if is_stress_run:
            handle.write(f"Precision/recall thresholds: {'PASS' if metric_ready else 'FAIL'}\n\n")
            handle.write(f"Strict score contract: {'PASS' if score_contract_ready else 'FAIL'}\n\n")
            handle.write(f"Overall strict contract: {'PASS' if overall_ready else 'FAIL'}\n\n")
            handle.write(
                "Stress mode intentionally overlaps normal and anomalous behavior. "
                "Use it as a robustness check, not as the canonical acceptance dataset.\n\n"
            )
        else:
            handle.write(f"Overall readiness: {'PASS' if overall_ready else 'FAIL'}\n\n")
        handle.write("```text\n")
        handle.write(summary_df.to_string(index=False))
        handle.write("\n```\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate fresh synthetic datasets and validate production readiness.")
    parser.add_argument("--sizes", nargs="*", type=int, default=[120, 500], help="Interview counts for fresh synthetic datasets.")
    parser.add_argument("--seeds", nargs="*", type=int, default=[11, 42, 99], help="Random seeds to validate.")
    parser.add_argument(
        "--formats",
        nargs="*",
        choices=sorted(FORMAT_TO_FILENAME),
        default=sorted(FORMAT_TO_FILENAME),
        help="Export formats to validate.",
    )
    parser.add_argument("--anomaly-ratio", type=float, default=0.2, help="Share of anomalous interviews.")
    parser.add_argument(
        "--difficulty",
        choices=["canonical", "stress"],
        default="canonical",
        help="Synthetic profile difficulty. Use stress to test overlapping normal/anomalous behavior.",
    )
    parser.add_argument("--parser", default="auto", choices=["auto", "surveycto", "odk"], help="Pipeline parser mode.")
    parser.add_argument("--detector-config", help="Optional JSON config file for anomaly detector thresholds/settings.")
    parser.add_argument("--data-root", default="data/generated_benchmarks", help="Where fresh synthetic datasets should be written.")
    parser.add_argument("--output-dir", default="output/production_validation", help="Where validation outputs should be written.")
    args = parser.parse_args()

    data_root = Path(args.data_root)
    output_root = Path(args.output_dir)
    detector_config = load_detector_config(args.detector_config) if args.detector_config else None
    summary_rows = []

    for size in args.sizes:
        for seed in args.seeds:
            dataset_name = sanitize_label(f"n{size}_seed{seed}")
            dataset_dir = data_root / dataset_name
            generated = build_dataset(
                dataset_size=size,
                seed=seed,
                anomaly_ratio=args.anomaly_ratio,
                output_dir=dataset_dir,
                difficulty=args.difficulty,
            )
            ground_truth_path = Path(generated["ground_truth_path"])

            for fmt in args.formats:
                raw_file = dataset_dir / FORMAT_TO_FILENAME[fmt]
                prefix = sanitize_label(f"{dataset_name}_{fmt}")
                run_output_dir = output_root / dataset_name / fmt
                metrics = evaluate_file(
                    raw_file,
                    ground_truth_path,
                    args.parser,
                    run_output_dir,
                    prefix,
                    detector_config=detector_config,
                )
                metrics.update(
                    {
                        "dataset": dataset_name,
                        "format": fmt,
                        "dataset_size": int(size),
                        "seed": int(seed),
                        "difficulty": args.difficulty,
                    }
                )
                summary_rows.append(metrics)

    summary_df = pd.DataFrame(summary_rows).sort_values(["dataset_size", "seed", "format"]).reset_index(drop=True)
    write_summary(summary_df, output_root)

    print("\nProduction readiness validation summary")
    print(summary_df.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
