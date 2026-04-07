#!/usr/bin/env python3
"""
Complete pipeline workflow for the SKACE-Time-Data project.
"""

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.resolve()
os.chdir(PROJECT_ROOT)


def run_command(cmd: list[str], description: str) -> bool:
    print(f"\n{'=' * 90}")
    print(f"STEP: {description}")
    print(f"{'=' * 90}")
    print("Command:", " ".join(cmd))

    started = time.time()
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    elapsed = time.time() - started

    if result.returncode == 0:
        print(f"\nOK in {elapsed:.2f}s")
        return True

    print(f"\nFAILED with exit code {result.returncode} after {elapsed:.2f}s")
    return False


def main() -> int:
    python_exe = sys.executable

    print("\n" + "=" * 90)
    print("SKACE TIME-DATA PIPELINE - COMPLETE WORKFLOW")
    print("=" * 90)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Using Python: {python_exe}")
    print("Note: evaluating n10000 may take several minutes.")

    steps = [
        (
            [python_exe, "tests/generate_synthetic_final.py", "--overwrite"],
            "1. Generate canonical synthetic logs and ground truth",
            True,
        ),
        (
            [
                python_exe,
                "run_pipeline.py",
                "--parser",
                "auto",
                "--output-dir",
                "output",
                "--ground-truth",
                "data/ground_truth_labels.csv",
                "--label",
                "canonical_validation",
                "--inputs",
                "data/odk.csv",
                "data/surveycto.csv",
            ],
            "2. Run pipeline on the canonical 24-interview validation set",
            True,
        ),
        (
            [
                python_exe,
                "analyze_pipeline_metrics.py",
                "--datasets",
                "n500",
                "n2000",
                "n10000",
                "--formats",
                "surveycto",
                "--parser",
                "surveycto",
                "--output-dir",
                "output",
            ],
            "3. Evaluate large synthetic datasets (SurveyCTO export)",
            True,
        ),
        (
            [
                python_exe,
                "analyze_pipeline_metrics.py",
                "--datasets",
                "n500",
                "--formats",
                "odk",
                "--parser",
                "auto",
                "--output-dir",
                "output",
            ],
            "4. Cross-format spot-check on the n500 ODK export",
            True,
        ),
        (
            [
                python_exe,
                "validate_production_readiness.py",
                "--sizes",
                "120",
                "500",
                "--seeds",
                "11",
                "42",
                "--formats",
                "surveycto",
                "odk",
                "--parser",
                "auto",
                "--data-root",
                "data/generated_benchmarks",
                "--output-dir",
                "output/production_validation",
            ],
            "5. Run fresh multi-seed production-readiness validation",
            True,
        ),
        (
            [
                python_exe,
                "threshold_recalibration.py",
                "--data-paths",
                "data/synthetic_datasets/n500/audit_logs_surveycto.csv",
                "--ground-truth",
                "data/synthetic_datasets/n500/ground_truth_labels.csv",
                "--parser",
                "surveycto",
                "--output-dir",
                "output",
            ],
            "6. Recompute threshold calibration on n500",
            True,
        ),
        (
            [
                python_exe,
                "feature_validation.py",
                "--data-paths",
                "data/synthetic_datasets/n500/audit_logs_surveycto.csv",
                "--ground-truth",
                "data/synthetic_datasets/n500/ground_truth_labels.csv",
                "--parser",
                "surveycto",
                "--output-dir",
                "output",
            ],
            "7. Recompute feature validation on n500",
            True,
        ),
        (
            [python_exe, "create_visualizations.py"],
            "8. Generate synthetic evaluation plots",
            False,
        ),
        (
            [python_exe, "generate_audit_notebook.py"],
            "9. Regenerate the primary audit notebook",
            False,
        ),
    ]

    for cmd, description, required in steps:
        success = run_command(cmd, description)
        if not success and required:
            print("\nAborting because a required workflow step failed.")
            return 1

    print(f"\n{'=' * 90}")
    print("PIPELINE WORKFLOW COMPLETE")
    print(f"{'=' * 90}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nKey outputs:")
    print("  - data/ground_truth_labels.csv")
    print("  - output/question_features_*.csv")
    print("  - output/section_features_*.csv")
    print("  - output/feature_dataset_*.csv")
    print("  - output/anomaly_report_*.csv")
    print("  - output/pipeline_output_*.csv")
    print("  - output/metrics_*.csv")
    print("  - output/synthetic_dataset_metrics.csv")
    print("  - output/synthetic_detection_by_type.csv")
    print("  - output/production_validation/production_readiness_summary.csv")
    print("  - output/detector_config_recalibrated.json")
    print("  - output/threshold_recalibration_results.txt")
    print("  - output/feature_validation_results.csv")
    print("  - output/synthetic_metrics_overview.png")
    print("  - output/synthetic_detection_by_type.png")
    print("  - notebooks/System_Audit_Report.ipynb")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
