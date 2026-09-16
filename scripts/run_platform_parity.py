#!/usr/bin/env python3
"""
Platform parity on matched conditions: one generated history, two formats.

The benchmark generator is normally called once per format, and the random
state advances between the two calls, so the SurveyCTO and ODK files of a
benchmark hold different interviews. Any difference in results between them
therefore mixes a parser effect with a sampling effect. This script removes
the sampling effect: each dataset is generated once and the same history is
rendered into both formats (AdversarialDataGenerator.generate_paired_benchmark).
The SurveyCTO rendering is identical to the file the robustness round used,
which the script checks, so its results are the ones already reported; the
ODK rendering is new.

For each dataset it reports, per format, the confusion counts of the default
detector, and across formats the number of interviews whose features, score
or category differ.

Usage:
    python scripts/run_platform_parity.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline.controller import PipelineController
from src.validation.reporting import compute_binary_metrics, merge_ground_truth
from tests.test_adversarial import AdversarialDataGenerator

DATA_ROOT = PROJECT_ROOT / "data" / "platform_parity"
OUTPUT_DIR = PROJECT_ROOT / "output" / "platform_parity"
DATASET_SIZE = 500
ANOMALY_RATIO = 0.2

# (label, seed, difficulty, SurveyCTO file the robustness round evaluated)
DATASETS = [
    ("canonical_seed42", 42, "canonical",
     PROJECT_ROOT / "data" / "synthetic_datasets" / "n500" / "audit_logs_surveycto.csv"),
    ("stress_seed7", 7, "stress",
     PROJECT_ROOT / "data" / "robustness_checks" / "n500_seed7_stress" / "audit_logs_surveycto.csv"),
    ("stress_seed99", 99, "stress",
     PROJECT_ROOT / "data" / "robustness_checks" / "n500_seed99_stress" / "audit_logs_surveycto.csv"),
]
FORMATS = ("surveycto", "odk")


def markdown_table(frame: pd.DataFrame) -> str:
    """Render a small table as Markdown without the optional tabulate dependency."""
    header = "| " + " | ".join(str(c) for c in frame.columns) + " |"
    rule = "|" + "|".join("---" for _ in frame.columns) + "|"
    body = ["| " + " | ".join(str(v) for v in row) + " |" for row in frame.itertuples(index=False)]
    return "\n".join([header, rule, *body])


def feature_columns(frame: pd.DataFrame) -> list[str]:
    return sorted(c for c in frame.columns if c[:2] in {"Q-", "S-", "V-", "T-"} and c[2:4].isdigit())


def generate(label: str, seed: int, difficulty: str) -> dict:
    generator = AdversarialDataGenerator(seed=seed, difficulty=difficulty)
    plan = generator.build_benchmark_plan(dataset_size=DATASET_SIZE, anomaly_ratio=ANOMALY_RATIO)
    surveycto_df, odk_df = generator.generate_paired_benchmark(plan)
    ground_truth = generator.build_ground_truth_from_plan(plan)

    out = DATA_ROOT / label
    out.mkdir(parents=True, exist_ok=True)
    paths = {"surveycto": out / "audit_logs_surveycto.csv", "odk": out / "audit_logs_odk.csv"}
    surveycto_df.to_csv(paths["surveycto"], index=False)
    odk_df.to_csv(paths["odk"], index=False)
    ground_truth.to_csv(out / "ground_truth_labels.csv", index=False)
    return {"paths": paths, "ground_truth": ground_truth}


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    metric_rows, difference_rows, summary_rows = [], [], []

    for label, seed, difficulty, round_surveycto in DATASETS:
        print(f"\n=== {label}: seed {seed}, {difficulty} difficulty ===")
        generated = generate(label, seed, difficulty)

        same_as_round = None
        if round_surveycto.exists():
            same_as_round = generated["paths"]["surveycto"].read_bytes() == round_surveycto.read_bytes()
        print(f"SurveyCTO rendering identical to the robustness-round file: {same_as_round}")

        results = {}
        for fmt in FORMATS:
            predictions = PipelineController(parser_type="auto").process_batch([generated["paths"][fmt]])
            predictions.to_csv(OUTPUT_DIR / f"pipeline_output_{label}_{fmt}.csv", index=False)
            merged = merge_ground_truth(generated["ground_truth"], predictions)
            m = compute_binary_metrics(merged)
            metric_rows.append({
                "dataset": label, "format": fmt,
                "tp": m["true_positive"], "fp": m["false_positive"],
                "fn": m["false_negative"], "tn": m["true_negative"],
                "precision": round(m["precision"], 4), "recall": round(m["recall"], 4),
                "f1": round(m["f1_score"], 4),
            })
            results[fmt] = predictions.set_index("interview_id").sort_index()

        scto, odk = results["surveycto"], results["odk"]
        if not scto.index.equals(odk.index):
            raise SystemExit(f"{label}: the two formats produced different interview sets")

        any_feature_differs = pd.Series(False, index=scto.index)
        for feature in feature_columns(scto):
            a = pd.to_numeric(scto[feature], errors="coerce").to_numpy(dtype=float)
            b = pd.to_numeric(odk[feature], errors="coerce").to_numpy(dtype=float)
            differs = ~np.isclose(a, b, rtol=1e-9, atol=1e-6, equal_nan=True)
            any_feature_differs |= differs
            if differs.any():
                difference_rows.append({
                    "dataset": label, "feature": feature,
                    "interviews_differing": int(differs.sum()),
                    "max_abs_difference": float(np.nanmax(np.abs(a - b))),
                })

        summary_rows.append({
            "dataset": label,
            "surveycto_identical_to_round_file": same_as_round,
            "interviews": int(len(scto)),
            "features_compared": len(feature_columns(scto)),
            "interviews_with_any_feature_difference": int(any_feature_differs.sum()),
            "interviews_with_score_difference": int((scto["anomaly_score"] != odk["anomaly_score"]).sum()),
            "interviews_with_category_difference": int((scto["anomaly_category"] != odk["anomaly_category"]).sum()),
        })

    metrics = pd.DataFrame(metric_rows)
    differences = pd.DataFrame(
        difference_rows, columns=["dataset", "feature", "interviews_differing", "max_abs_difference"]
    )
    summary = pd.DataFrame(summary_rows)
    metrics.to_csv(OUTPUT_DIR / "parity_metrics.csv", index=False)
    differences.to_csv(OUTPUT_DIR / "parity_feature_differences.csv", index=False)
    summary.to_csv(OUTPUT_DIR / "parity_summary.csv", index=False)

    lines = [
        "# Platform parity on matched conditions",
        "",
        "One generated history per dataset, rendered into both formats and evaluated",
        "with the default detector. Generated by `scripts/run_platform_parity.py`.",
        "",
        "## Detector results per format",
        "",
        markdown_table(metrics),
        "",
        "## Cross-format differences",
        "",
        markdown_table(summary),
        "",
        "## Features that differ between formats",
        "",
        markdown_table(differences) if not differences.empty else "None.",
        "",
    ]
    (OUTPUT_DIR / "parity_summary.md").write_text("\n".join(lines), encoding="utf-8")

    print("\n" + metrics.to_string(index=False))
    print("\n" + summary.to_string(index=False))
    if not differences.empty:
        print("\n" + differences.to_string(index=False))
    print(f"\nWritten to {OUTPUT_DIR.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
