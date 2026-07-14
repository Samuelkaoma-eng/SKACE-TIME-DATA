#!/usr/bin/env python3
"""
Reproduce the robustness validation round reported in the validation report.

The round consists of three experiments, all on datasets whose seeds were never
used during development or calibration:

1. A class imbalance sweep: n=500, seed 7, canonical difficulty, SurveyCTO
   format, anomaly prevalence at 5, 10, 20 and 30 percent.
2. Held-out stress evaluation: n=500, seeds 7 and 99, stress difficulty,
   both platform formats.
3. A canonical regression check: the n=500 seed 42 benchmark in both formats.

Datasets are regenerated into data/robustness_checks/ and evaluated with the
default detector configuration. Outputs are written to
output/robustness_validation/ with the same labels used in the validation
report.

Usage:
    python scripts/run_robustness_validation.py
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data" / "robustness_checks"
BENCHMARK_ROOT = PROJECT_ROOT / "data" / "synthetic_datasets" / "n500"
OUTPUT_DIR = PROJECT_ROOT / "output" / "robustness_validation"

SWEEP_RATIOS = [(0.05, "r005"), (0.10, "r010"), (0.20, "r020"), (0.30, "r030")]
STRESS_SEEDS = [7, 99]


def run(cmd: list[str], description: str) -> None:
    print(f"\n{'=' * 80}\n{description}\n{'=' * 80}")
    print("Command:", " ".join(str(c) for c in cmd))
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print(f"FAILED: {description}")
        raise SystemExit(result.returncode)


def main() -> int:
    py = sys.executable
    gen = PROJECT_ROOT / "tests" / "generate_benchmark_datasets.py"
    pipe = PROJECT_ROOT / "run_pipeline.py"

    # 1. Regenerate the robustness datasets from their recorded seeds.
    for ratio, tag in SWEEP_RATIOS:
        run(
            [py, str(gen), "--dataset-size", "500", "--seed", "7",
             "--anomaly-ratio", str(ratio),
             "--output-dir", str(DATA_ROOT / f"n500_seed7_{tag}")],
            f"Generate sweep dataset, anomaly ratio {ratio}",
        )
    for seed in STRESS_SEEDS:
        run(
            [py, str(gen), "--dataset-size", "500", "--seed", str(seed),
             "--difficulty", "stress",
             "--output-dir", str(DATA_ROOT / f"n500_seed{seed}_stress")],
            f"Generate stress dataset, seed {seed}",
        )

    # 2. Class imbalance sweep (SurveyCTO format).
    for _, tag in SWEEP_RATIOS:
        ds = DATA_ROOT / f"n500_seed7_{tag}"
        run(
            [py, str(pipe),
             "--inputs", str(ds / "audit_logs_surveycto.csv"),
             "--ground-truth", str(ds / "ground_truth_labels.csv"),
             "--label", f"sweep_{tag}",
             "--output-dir", str(OUTPUT_DIR)],
            f"Evaluate imbalance sweep {tag}",
        )

    # 3. Held-out stress evaluation, both formats.
    for seed in STRESS_SEEDS:
        ds = DATA_ROOT / f"n500_seed{seed}_stress"
        for fmt in ("surveycto", "odk"):
            run(
                [py, str(pipe),
                 "--inputs", str(ds / f"audit_logs_{fmt}.csv"),
                 "--ground-truth", str(ds / "ground_truth_labels.csv"),
                 "--label", f"stress_seed{seed}_{fmt}",
                 "--output-dir", str(OUTPUT_DIR)],
                f"Evaluate stress seed {seed}, {fmt}",
            )

    # 4. Canonical n500 regression check, both formats.
    for fmt in ("surveycto", "odk"):
        run(
            [py, str(pipe),
             "--inputs", str(BENCHMARK_ROOT / f"audit_logs_{fmt}.csv"),
             "--ground-truth", str(BENCHMARK_ROOT / "ground_truth_labels.csv"),
             "--label", f"benchmark_n500_{fmt}",
             "--output-dir", str(OUTPUT_DIR)],
            f"Canonical n500 regression check, {fmt}",
        )

    # 5. Print the consolidated metric table.
    import json

    print(f"\n{'=' * 80}\nROBUSTNESS ROUND SUMMARY\n{'=' * 80}")
    labels = [f"sweep_{tag}" for _, tag in SWEEP_RATIOS]
    labels += [f"stress_seed{seed}_{fmt}" for seed in STRESS_SEEDS for fmt in ("surveycto", "odk")]
    labels += [f"benchmark_n500_{fmt}" for fmt in ("surveycto", "odk")]
    for label in labels:
        metrics_path = OUTPUT_DIR / f"metrics_{label}.json"
        with metrics_path.open(encoding="utf-8") as handle:
            m = json.load(handle)
        if isinstance(m, list):
            m = m[0]
        print(f"{label:28s} precision={m['precision']:.4f} recall={m['recall']:.4f} f1={m['f1_score']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
