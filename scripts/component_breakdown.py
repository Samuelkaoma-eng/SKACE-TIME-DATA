#!/usr/bin/env python3
"""
Separate performance breakdowns for the IQR-based and rule-based components.

The proposal (Section 5) requires that the relative contribution of each
detection component be assessed, not only the performance of the two together.
This script produces that breakdown from the recorded predictions of the
robustness round, so it reports the frozen evaluation rather than a fresh run.

How each component is isolated:

  Combined   the shipped detector. anomaly_score >= behavior_score_threshold,
             where anomaly_score = min(iqr_flags, 1) + rule_flags.

  IQR only   iqr_flags >= 1. The IQR contribution to the combined score is
             capped at one, deliberately, so that several correlated duration,
             mean and variance outliers arising from the same underlying timing
             pattern cannot be counted repeatedly. That cap makes the combined
             threshold of two unreachable for this component on its own, so the
             only meaningful standalone criterion is whether any IQR fence fired.

  Rules only rule_flags >= behavior_score_threshold. The same threshold the
             combined detector applies, with the IQR contribution removed.

Usage:
    python scripts/component_breakdown.py
"""

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREDICTIONS_DIR = PROJECT_ROOT / "output" / "robustness_validation"
BEHAVIOR_SCORE_THRESHOLD = 2


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


def main() -> int:
    paths = sorted(PREDICTIONS_DIR.glob("predictions_*.csv"))
    if not paths:
        print(f"No predictions found in {PREDICTIONS_DIR}", file=sys.stderr)
        return 1

    rows = []
    for path in paths:
        frame = pd.read_csv(path)
        truth = frame["is_anomalous"]
        components = {
            "Combined": frame["anomaly_score"] >= BEHAVIOR_SCORE_THRESHOLD,
            "IQR only": frame["iqr_flags"] >= 1,
            "Rules only": frame["rule_flags"] >= BEHAVIOR_SCORE_THRESHOLD,
        }
        for name, predicted in components.items():
            rows.append({"run": path.stem.replace("predictions_", ""),
                         "component": name, **scores(truth, predicted.astype(int))})

    results = pd.DataFrame(rows)

    print("Per-run breakdown\n")
    header = f"{'run':<26} {'component':<11} {'P':>7} {'R':>7} {'F1':>7}   {'TP':>4} {'FP':>4} {'FN':>4}"
    print(header)
    print("-" * len(header))
    for run, group in results.groupby("run", sort=True):
        for _, r in group.iterrows():
            print(f"{run:<26} {r['component']:<11} {r['precision']:>7.4f} {r['recall']:>7.4f} "
                  f"{r['f1']:>7.4f}   {r['tp']:>4} {r['fp']:>4} {r['fn']:>4}")
        print()

    print("\nAggregated over every run\n")
    header = f"{'component':<11} {'P':>7} {'R':>7} {'F1':>7}   {'TP':>5} {'FP':>5} {'FN':>5}"
    print(header)
    print("-" * len(header))
    for component in ("Combined", "IQR only", "Rules only"):
        sub = results[results.component == component]
        tp, fp, fn = int(sub.tp.sum()), int(sub.fp.sum()), int(sub.fn.sum())
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        print(f"{component:<11} {precision:>7.4f} {recall:>7.4f} {f1:>7.4f}   {tp:>5} {fp:>5} {fn:>5}")

    out = PREDICTIONS_DIR / "component_breakdown.csv"
    results.to_csv(out, index=False)
    print(f"\nWritten to {out.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
