import argparse
import json
import time
from pathlib import Path

import pandas as pd

from src.pipeline.controller import PipelineController
from src.validation.detector_config import load_detector_config
from src.validation.reporting import compute_binary_metrics, compute_detection_by_type, load_ground_truth, merge_ground_truth


DATASET_FILES = {
    "surveycto": "audit_logs_surveycto.csv",
    "odk": "audit_logs_odk.csv",
}

def evaluate_dataset(
    dataset_dir: Path,
    formats: list[str],
    parser_type: str,
    detector_config: dict | None = None,
    output_dir: Path | None = None,
) -> tuple[list[dict], list[dict]]:
    ground_truth = load_ground_truth(dataset_dir / "ground_truth_labels.csv")
    rows = []
    type_rows = []

    for fmt in formats:
        file_path = dataset_dir / DATASET_FILES[fmt]
        if not file_path.exists():
            continue

        controller = PipelineController(parser_type=parser_type, detector_config=detector_config)
        started = time.time()
        predictions = controller.process_batch([file_path])
        runtime = time.time() - started

        merged = merge_ground_truth(ground_truth, predictions)
        metrics = compute_binary_metrics(merged)
        metrics.update(
            {
                "dataset": dataset_dir.name,
                "format": fmt,
                "runtime_seconds": round(runtime, 2),
                "source_file": str(file_path),
            }
        )
        rows.append(metrics)

        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            merged.to_csv(output_dir / f"synthetic_predictions_{dataset_dir.name}_{fmt}.csv", index=False)

        for row in compute_detection_by_type(merged):
            row.update({"dataset": dataset_dir.name, "format": fmt})
            type_rows.append(row)

    return rows, type_rows


def discover_dataset_dirs(root: Path, datasets: list[str] | None) -> list[Path]:
    if datasets:
        return [root / name for name in datasets]
    return sorted(path for path in root.iterdir() if path.is_dir() and path.name.startswith("n"))


def save_report(metrics_df: pd.DataFrame, type_df: pd.DataFrame, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = out_dir / "synthetic_dataset_metrics.csv"
    if metrics_path.exists():
        existing_metrics = pd.read_csv(metrics_path)
        metrics_df = pd.concat([existing_metrics, metrics_df], ignore_index=True)
        metrics_df = metrics_df.drop_duplicates(subset=["dataset", "format"], keep="last")
    metrics_df = metrics_df.sort_values(["dataset", "format"]).reset_index(drop=True)
    metrics_df.to_csv(metrics_path, index=False)

    if not type_df.empty:
        type_path = out_dir / "synthetic_detection_by_type.csv"
        if type_path.exists():
            existing_types = pd.read_csv(type_path)
            type_df = pd.concat([existing_types, type_df], ignore_index=True)
            type_df = type_df.drop_duplicates(subset=["dataset", "format", "anomaly_type"], keep="last")
        type_df = type_df.sort_values(["dataset", "format", "anomaly_type"]).reset_index(drop=True)
        type_df.to_csv(type_path, index=False)

    summary_path = out_dir / "synthetic_dataset_metrics.md"
    with summary_path.open("w", encoding="utf-8") as handle:
        handle.write("# Synthetic Dataset Evaluation\n\n")
        handle.write("## Metrics\n\n```text\n")
        handle.write(metrics_df.to_string(index=False))
        handle.write("\n```\n\n")
        if not type_df.empty:
            handle.write("## Detection By Type\n\n```text\n")
            handle.write(type_df.to_string(index=False))
            handle.write("\n```\n")


def print_summary(metrics_df: pd.DataFrame, type_df: pd.DataFrame) -> None:
    print("\nSynthetic dataset metrics")
    print(metrics_df.to_string(index=False))
    if not type_df.empty:
        print("\nDetection by anomaly type")
        print(type_df.to_string(index=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate pipeline performance on synthetic datasets.")
    parser.add_argument(
        "--datasets",
        nargs="*",
        help="Dataset directory names under data/synthetic_datasets, for example: n500 n2000",
    )
    parser.add_argument(
        "--formats",
        nargs="*",
        choices=sorted(DATASET_FILES),
        default=sorted(DATASET_FILES),
        help="Survey export formats to evaluate. Default: both surveycto and odk.",
    )
    parser.add_argument(
        "--synthetic-root",
        default="data/synthetic_datasets",
        help="Root directory containing synthetic dataset folders.",
    )
    parser.add_argument(
        "--parser",
        default="auto",
        choices=["auto", "surveycto", "odk"],
        help="Parser routing mode for PipelineController.",
    )
    parser.add_argument("--detector-config", help="Optional JSON config file for anomaly detector thresholds/settings.")
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory where evaluation reports should be written.",
    )
    args = parser.parse_args()

    root = Path(args.synthetic_root)
    dataset_dirs = discover_dataset_dirs(root, args.datasets)
    if not dataset_dirs:
        raise FileNotFoundError(f"No dataset directories found under {root}")

    detector_config = load_detector_config(args.detector_config) if args.detector_config else None
    metric_rows = []
    type_rows = []
    for dataset_dir in dataset_dirs:
        rows, by_type = evaluate_dataset(
            dataset_dir,
            args.formats,
            args.parser,
            detector_config=detector_config,
            output_dir=Path(args.output_dir),
        )
        metric_rows.extend(rows)
        type_rows.extend(by_type)

    metrics_df = pd.DataFrame(metric_rows)
    type_df = pd.DataFrame(type_rows)

    save_report(metrics_df, type_df, Path(args.output_dir))
    print_summary(metrics_df, type_df)

    json_path = Path(args.output_dir) / "synthetic_dataset_metrics.json"
    metrics_for_json = pd.read_csv(Path(args.output_dir) / "synthetic_dataset_metrics.csv")
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(metrics_for_json.to_dict(orient="records"), handle, indent=2)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
