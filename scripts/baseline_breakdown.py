#!/usr/bin/env python3
"""
Both current-practice baselines on every run of the robustness round.

Section 6.3 compares the full detector with two baselines on the canonical
n500 SurveyCTO benchmark. This script applies the same two baselines to every
recorded run of the robustness round, including the four held-out stress
runs, so the comparison is also reported under the condition where profiles
overlap.

  Duration IQR  flags an interview whose V-01 total duration falls outside the
                Tukey fences (1.5 x IQR) estimated from that run, the same
                construction as duration_iqr_baseline_metrics in
                scripts/strict_examiner_audit.py.
  V-10 rule     flags an interview whose V-10_zero_back_nav_flag is set, that
                is whose log contains a run of twenty or more consecutive
                events with no back or jump event, the same rule as
                zero_back_nav_baseline_metrics in that script.
  Full detector the shipped detector's behavioural decision, as recorded.

Everything is computed from the recorded feature datasets and predictions of
the robustness round, so no pipeline is re-run.

Usage:
    python scripts/baseline_breakdown.py
"""

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = PROJECT_ROOT / "output" / "robustness_validation"
CLASSES = ["speeding", "disengaged", "fabricated"]


def scores(truth: pd.Series, predicted: pd.Series) -> dict:
    tp = int(((truth == 1) & (predicted == 1)).sum())
    fp = int(((truth == 0) & (predicted == 1)).sum())
    fn = int(((truth == 1) & (predicted == 0)).sum())
    tn = int(((truth == 0) & (predicted == 0)).sum())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": precision, "recall": recall, "f1": f1}


def duration_iqr_flags(durations: pd.Series, multiplier: float = 1.5) -> pd.Series:
    q1, q3 = durations.quantile(0.25), durations.quantile(0.75)
    iqr = q3 - q1
    return ((durations < q1 - multiplier * iqr) | (durations > q3 + multiplier * iqr)).astype(int)


def main() -> int:
    prediction_paths = sorted(RUN_DIR.glob("predictions_*.csv"))
    if not prediction_paths:
        print(f"No predictions found in {RUN_DIR}", file=sys.stderr)
        return 1

    rows = []
    for path in prediction_paths:
        run = path.stem.replace("predictions_", "")
        predictions = pd.read_csv(path)
        features = pd.read_csv(RUN_DIR / f"feature_dataset_{run}.csv")
        frame = predictions.merge(
            features[["interview_id", "V-01_total_interview_duration_ms", "V-10_zero_back_nav_flag"]],
            on="interview_id", how="inner", validate="one_to_one",
        )
        if len(frame) != len(predictions):
            raise SystemExit(f"{run}: features and predictions cover different interviews")

        truth = frame["is_anomalous"].astype(int)
        methods = {
            "Full detector": frame["predicted_is_anomalous_behavior"].astype(int),
            "Duration IQR": duration_iqr_flags(frame["V-01_total_interview_duration_ms"]),
            "V-10 rule": frame["V-10_zero_back_nav_flag"].fillna(0).astype(int),
        }
        for method, predicted in methods.items():
            row = {"run": run, "method": method, **scores(truth, predicted)}
            for cls in CLASSES:
                mask = frame["anomaly_type"].astype(str).str.lower() == cls
                row[f"{cls}_detected"] = int(predicted[mask].sum())
                row[f"{cls}_total"] = int(mask.sum())
            rows.append(row)

    results = pd.DataFrame(rows)
    out = RUN_DIR / "baseline_breakdown.csv"
    results.to_csv(out, index=False)

    print("Per-run comparison\n")
    header = f"{'run':<26} {'method':<14} {'P':>7} {'R':>7} {'F1':>7}   {'TP':>4} {'FP':>4} {'FN':>4}"
    print(header)
    print("-" * len(header))
    for run, group in results.groupby("run", sort=True):
        for _, r in group.iterrows():
            print(f"{run:<26} {r['method']:<14} {r['precision']:>7.4f} {r['recall']:>7.4f} "
                  f"{r['f1']:>7.4f}   {r['tp']:>4} {r['fp']:>4} {r['fn']:>4}")
        print()

    stress = results[results["run"].str.startswith("stress_")]
    print("Aggregated over the four held-out stress runs\n")
    for method in ("Full detector", "Duration IQR", "V-10 rule"):
        sub = stress[stress["method"] == method]
        total = scores(pd.Series([1] * int(sub.tp.sum() + sub.fn.sum()) + [0] * int(sub.fp.sum() + sub.tn.sum())),
                       pd.Series([1] * int(sub.tp.sum()) + [0] * int(sub.fn.sum())
                                 + [1] * int(sub.fp.sum()) + [0] * int(sub.tn.sum())))
        per_class = ", ".join(
            f"{cls} {int(sub[f'{cls}_detected'].sum())}/{int(sub[f'{cls}_total'].sum())}" for cls in CLASSES
        )
        print(f"{method:<14} P={total['precision']:.4f} R={total['recall']:.4f} F1={total['f1']:.4f}  ({per_class})")

    print(f"\nWritten to {out.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
