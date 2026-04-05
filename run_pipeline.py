import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Union

from src.pipeline.controller import PipelineController
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


def process_interview(filepath: Union[str, Path], parser_type: str = 'auto') -> List[dict]:
    """
    Public API wrapper: process a single paradata file and return a list of
    per-interview feature dictionaries.

    Used by test_pipeline.py and any external caller that needs a simple
    functional interface without instantiating PipelineController directly.

    Parameters
    ----------
    filepath : str or Path
        Path to the raw audit log CSV.
    parser_type : str
        One of 'auto', 'surveycto', 'odk'. Default = 'auto'.

    Returns
    -------
    List[dict]
        One dictionary per interview found in the file.
    """
    controller = PipelineController(parser_type=parser_type)
    return controller.process_file(filepath)

def interactive_cli(data_dir: Path):
    """Provide an interactive CLI to select a dataset if multiple exist."""
    print("=== Paradata Feature Extraction Pipeline ===")
    
    csv_files = list(data_dir.glob("*.csv"))

    if not csv_files:
        print(f"No CSV files found in '{data_dir.absolute()}'.")
        print("Please place your audit logs into the 'data/' directory.")
        return None
        
    print("\nAvailable datasets:")
    for idx, file_path in enumerate(csv_files, 1):
        print(f"  {idx}. {file_path.name}")
        
    while True:
        try:
            choice = input(f"\nSelect dataset to process (1-{len(csv_files)}) or 'all': ").strip()
            if choice.lower() == 'all':
                return csv_files
            
            idx = int(choice)
            if 1 <= idx <= len(csv_files):
                return [csv_files[idx-1]]
            else:
                print(f"Invalid choice. Please enter a number between 1 and {len(csv_files)}.")
        except ValueError:
            print("Invalid input. Please enter a number or 'all'.")


def build_run_label(csv_files: List[Path], explicit_label: str | None, timestamp: str) -> str:
    if explicit_label:
        return sanitize_label(explicit_label)
    if len(csv_files) == 1:
        return sanitize_label(csv_files[0].stem)
    return sanitize_label(f"batch_{timestamp}")

def main():
    parser = argparse.ArgumentParser(description="Run the academic paradata pipeline.")
    parser.add_argument("--data-dir", default="data", help="Raw audit log directory")
    parser.add_argument("--output-dir", default="output", help="Features output directory")
    parser.add_argument("--parser", default="auto", choices=["auto", "surveycto", "odk"], help="Parser type")
    parser.add_argument("--interactive", action="store_true", help="Launch interactive UI")
    parser.add_argument("--inputs", nargs="*", help="Optional explicit CSV files to process")
    parser.add_argument("--ground-truth", help="Optional labelled ground-truth CSV for metric generation")
    parser.add_argument("--label", help="Optional stable label to use in output filenames")
    parser.add_argument(
        "--write-legacy-outputs",
        action="store_true",
        help="Also write legacy compatibility files (features_output_*.csv and anomaly_report.csv).",
    )
    
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    
    data_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if args.inputs:
        csv_files = [Path(path) for path in args.inputs]
        missing_files = [str(path) for path in csv_files if not path.exists()]
        if missing_files:
            print(f"Missing input files: {', '.join(missing_files)}")
            return 1
    elif args.interactive or len(sys.argv) == 1:
        csv_files = interactive_cli(data_dir)
        if not csv_files:
            return 0
    else:
        csv_files = list(data_dir.rglob("*.csv"))
        if not csv_files:
            print(f"No CSV files found in '{data_dir.absolute()}' or its subdirectories.")
            return 0
            
    print(f"\nInitializing Pipeline Controller with config: Parser = {args.parser.upper()}")
    controller = PipelineController(parser_type=args.parser)
    
    print(f"Beginning Batch Processing for {len(csv_files)} files...")
    final_df = controller.process_batch(csv_files)
    
    if final_df.empty:
        print("No features extracted. Pipeline failed or data was invalid.")
        return 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_label = build_run_label(csv_files, args.label, timestamp)

    feature_dataset = feature_dataset_view(final_df)
    anomaly_report = anomaly_report_view(final_df)

    feature_dataset_file = output_dir / f"feature_dataset_{run_label}.csv"
    anomaly_report_file = output_dir / f"anomaly_report_{run_label}.csv"
    combined_output_file = output_dir / f"pipeline_output_{run_label}.csv"

    feature_dataset.to_csv(feature_dataset_file, index=False, na_rep="NaN")
    anomaly_report.to_csv(anomaly_report_file, index=False, na_rep="NaN")
    final_df.to_csv(combined_output_file, index=False, na_rep="NaN")

    if args.write_legacy_outputs:
        legacy_feature_file = output_dir / f"features_output_{timestamp}.csv"
        legacy_anomaly_file = output_dir / "anomaly_report.csv"
        feature_dataset.to_csv(legacy_feature_file, index=False, na_rep="NaN")
        anomaly_report.to_csv(legacy_anomaly_file, index=False, na_rep="NaN")

    print(f"\nFeatures engineered for {len(final_df)} extracted interviews.")
    print("Anomaly Detection Rules (IQR + Entropy + Speed) successfully applied.")
    print(f"Feature dataset written to: {feature_dataset_file.absolute()}")
    print(f"Anomaly report written to: {anomaly_report_file.absolute()}")
    print(f"Combined pipeline dataset written to: {combined_output_file.absolute()}")
    if args.write_legacy_outputs:
        print("Legacy compatibility files also written to output/.")

    if args.ground_truth:
        ground_truth_path = Path(args.ground_truth)
        if not ground_truth_path.exists():
            print(f"Ground truth file not found: {ground_truth_path}")
            return 1

        ground_truth = load_ground_truth(ground_truth_path)
        merged = merge_ground_truth(ground_truth, final_df)
        metrics = compute_binary_metrics(merged)
        detection_rows = compute_detection_by_type(merged)
        artifact_paths = save_evaluation_artifacts(metrics, merged, output_dir, run_label, detection_rows)

        print("\nLabelled evaluation completed.")
        print(
            f"Precision={metrics['precision']:.4f} "
            f"Recall={metrics['recall']:.4f} "
            f"F1={metrics['f1_score']:.4f}"
        )
        print(
            "Acceptance checks: "
            f"precision={metrics['passes_precision_threshold']} "
            f"recall={metrics['passes_recall_threshold']} "
            f"fabricated_score={metrics['passes_fabricated_score_threshold']} "
            f"normal_score={metrics['passes_normal_score_threshold']}"
        )
        print(f"Merged predictions written to: {Path(artifact_paths['predictions_csv']).absolute()}")
        print(f"Metrics summary written to: {Path(artifact_paths['metrics_md']).absolute()}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
