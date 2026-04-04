import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu
from statsmodels.stats.multitest import multipletests

from src.pipeline.controller import PipelineController


EXCLUDE_COLUMNS = {
    "file_name",
    "interview_id",
    "anomaly_category",
    "anomaly_score",
    "status",
    "flagged_features",
    "ground_truth_is_anomalous",
    "is_anomalous",
    "is_anomalous_behavior",
    "is_data_quality_issue",
}


def run_pipeline(data_paths: list[str], parser_type: str) -> pd.DataFrame:
    controller = PipelineController(parser_type=parser_type)
    return controller.process_batch(data_paths)


def prepare_eval_frame(results_df: pd.DataFrame, ground_truth_path: str) -> pd.DataFrame:
    gt = pd.read_csv(ground_truth_path)
    required = {"interview_id", "is_anomalous"}
    missing = required - set(gt.columns)
    if missing:
        raise ValueError(f"Ground truth is missing columns {sorted(missing)}")

    df = results_df.copy()
    df["interview_id"] = df["interview_id"].astype(str)
    gt["interview_id"] = gt["interview_id"].astype(str)
    gt = gt.rename(columns={"is_anomalous": "ground_truth_is_anomalous"})
    merged = gt.merge(df, on="interview_id", how="inner", validate="one_to_one")
    if merged.empty:
        raise ValueError("No matching interview IDs were found between predictions and ground truth")
    return merged


def compute_feature_stats(eval_df: pd.DataFrame, alpha: float) -> pd.DataFrame:
    numeric_cols = eval_df.select_dtypes(include=[np.number]).columns
    feature_cols = [col for col in numeric_cols if col not in EXCLUDE_COLUMNS and col != "is_anomalous"]

    normal = eval_df[eval_df["ground_truth_is_anomalous"] == 0]
    anomalous = eval_df[eval_df["ground_truth_is_anomalous"] == 1]
    if normal.empty or anomalous.empty:
        raise ValueError("Both normal and anomalous examples are required for feature validation")

    rows = []
    for feature in feature_cols:
        normal_values = normal[feature].dropna()
        anomalous_values = anomalous[feature].dropna()
        if len(normal_values) < 3 or len(anomalous_values) < 3:
            continue

        stat, p_value = mannwhitneyu(normal_values, anomalous_values, alternative="two-sided")
        n1, n2 = len(normal_values), len(anomalous_values)
        effect_size = abs((2 * stat / (n1 * n2)) - 1)

        rows.append(
            {
                "feature": feature,
                "p_value": float(p_value),
                "statistic": float(stat),
                "effect_size": float(effect_size),
                "normal_mean": float(normal_values.mean()),
                "anomalous_mean": float(anomalous_values.mean()),
                "normal_std": float(normal_values.std()),
                "anomalous_std": float(anomalous_values.std()),
                "normal_n": int(n1),
                "anomalous_n": int(n2),
            }
        )

    stats_df = pd.DataFrame(rows)
    if stats_df.empty:
        return stats_df

    rejected, adjusted, _, _ = multipletests(stats_df["p_value"], alpha=alpha, method="bonferroni")
    stats_df["p_adjusted"] = adjusted
    stats_df["significant"] = rejected
    stats_df = stats_df.sort_values(["significant", "effect_size", "p_value"], ascending=[False, False, True])
    return stats_df


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate feature significance on labelled data.")
    parser.add_argument("--data-paths", nargs="+", required=True, help="One or more raw audit CSV files to process.")
    parser.add_argument("--ground-truth", required=True, help="CSV containing interview_id and is_anomalous.")
    parser.add_argument("--parser", default="auto", choices=["auto", "surveycto", "odk"])
    parser.add_argument("--alpha", type=float, default=0.05, help="Bonferroni-adjusted significance level.")
    parser.add_argument("--output-dir", default="output", help="Directory to write validation outputs.")
    args = parser.parse_args()

    results_df = run_pipeline(args.data_paths, args.parser)
    eval_df = prepare_eval_frame(results_df, args.ground_truth)
    stats_df = compute_feature_stats(eval_df, args.alpha)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "feature_validation_results.csv"
    stats_df.to_csv(csv_path, index=False)

    txt_path = output_dir / "feature_validation_results.txt"
    significant_count = int(stats_df["significant"].sum()) if not stats_df.empty else 0
    with txt_path.open("w", encoding="utf-8") as handle:
        handle.write("Feature Validation Results\n")
        handle.write("=========================\n\n")
        handle.write(f"Data paths: {', '.join(args.data_paths)}\n")
        handle.write(f"Ground truth: {args.ground_truth}\n")
        handle.write(f"Sample size: {len(eval_df)}\n")
        handle.write(f"Alpha: {args.alpha}\n")
        handle.write(f"Features tested: {len(stats_df)}\n")
        handle.write(f"Significant features: {significant_count}\n\n")
        if not stats_df.empty:
            handle.write(stats_df.to_string(index=False))
            handle.write("\n")

    print(f"Processed {len(eval_df)} labelled interviews")
    print(f"Features tested: {len(stats_df)}")
    print(f"Significant features: {significant_count}")
    print(f"Saved detailed results to: {csv_path}")
    print(f"Saved summary to: {txt_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
