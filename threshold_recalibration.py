import argparse
import json
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import auc, f1_score, precision_score, recall_score, roc_curve

from src.pipeline.controller import PipelineController
from src.validation.detector_config import build_recalibrated_detector_config, load_detector_config
from src.validation.reporting import load_ground_truth as load_ground_truth_df

matplotlib.use("Agg")


def run_pipeline(data_paths: list[str], parser_type: str, detector_config: dict | None = None) -> pd.DataFrame:
    controller = PipelineController(parser_type=parser_type, detector_config=detector_config)
    return controller.process_batch(data_paths)


def load_ground_truth(path: str) -> dict[str, int]:
    gt = load_ground_truth_df(path)
    return dict(zip(gt["interview_id"].astype(str), gt["is_anomalous"].astype(int)))


def prepare_eval_frame(results_df: pd.DataFrame, ground_truth_dict: dict[str, int]) -> pd.DataFrame:
    eval_df = results_df.copy()
    eval_df["interview_id"] = eval_df["interview_id"].astype(str)
    eval_df["is_anomalous_gt"] = eval_df["interview_id"].map(ground_truth_dict)
    eval_df = eval_df.dropna(subset=["is_anomalous_gt", "anomaly_score"])
    if eval_df.empty:
        raise ValueError("No matching interview IDs were found between predictions and ground truth")
    eval_df["is_anomalous_gt"] = eval_df["is_anomalous_gt"].astype(int)
    eval_df["is_data_quality_issue"] = eval_df.get("is_data_quality_issue", 0).fillna(0).astype(int)
    return eval_df


def evaluate_thresholds(eval_df: pd.DataFrame, thresholds: np.ndarray) -> tuple[float, dict, pd.DataFrame]:
    y_true = eval_df["is_anomalous_gt"].to_numpy()
    rows = []
    best_threshold = 2.0
    best_metrics = {"f1_score": -1.0}

    for threshold in thresholds:
        behavior_pred = (eval_df["anomaly_score"].to_numpy() >= threshold).astype(int)
        y_pred = np.maximum(behavior_pred, eval_df["is_data_quality_issue"].to_numpy())

        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)

        row = {
            "threshold": float(threshold),
            "precision": float(precision),
            "recall": float(recall),
            "f1_score": float(f1),
        }
        rows.append(row)

        if f1 > best_metrics["f1_score"]:
            best_threshold = float(threshold)
            best_metrics = row

    return best_threshold, best_metrics, pd.DataFrame(rows)


def save_roc_curve(eval_df: pd.DataFrame, output_path: Path) -> float:
    y_true = eval_df["is_anomalous_gt"].to_numpy()
    scores = eval_df["anomaly_score"].to_numpy()
    fpr, tpr, _ = roc_curve(y_true, scores)
    roc_auc = auc(fpr, tpr)

    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, color="darkorange", lw=2, label=f"ROC curve (AUC = {roc_auc:.3f})")
    plt.plot([0, 1], [0, 1], color="navy", lw=2, linestyle="--")
    plt.xlim(0.0, 1.0)
    plt.ylim(0.0, 1.05)
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curve for Anomaly Score")
    plt.legend(loc="lower right")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    return float(roc_auc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Recalibrate anomaly score thresholds on labelled data.")
    parser.add_argument("--data-paths", nargs="+", required=True, help="One or more raw audit CSV files to process.")
    parser.add_argument("--ground-truth", required=True, help="CSV containing interview_id and is_anomalous.")
    parser.add_argument("--parser", default="auto", choices=["auto", "surveycto", "odk"])
    parser.add_argument("--detector-config", help="Optional JSON config file for anomaly detector thresholds/settings.")
    parser.add_argument("--output-dir", default="output", help="Directory to write recalibration outputs.")
    args = parser.parse_args()

    detector_config = load_detector_config(args.detector_config) if args.detector_config else None
    results_df = run_pipeline(args.data_paths, args.parser, detector_config=detector_config)
    ground_truth = load_ground_truth(args.ground_truth)
    eval_df = prepare_eval_frame(results_df, ground_truth)

    thresholds = np.arange(0.5, max(5.1, eval_df["anomaly_score"].max() + 0.6), 0.1)
    optimal_threshold, best_metrics, threshold_df = evaluate_thresholds(eval_df, thresholds)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    threshold_path = output_dir / "threshold_recalibration_curve.csv"
    threshold_df.to_csv(threshold_path, index=False)

    roc_path = output_dir / "threshold_roc_curve.png"
    roc_auc = save_roc_curve(eval_df, roc_path)

    detector_config_payload = build_recalibrated_detector_config(
        behavior_score_threshold=optimal_threshold,
        data_paths=args.data_paths,
        ground_truth_path=args.ground_truth,
        base_config=detector_config,
    )
    detector_config_path = output_dir / "detector_config_recalibrated.json"
    detector_config_path.write_text(json.dumps(detector_config_payload, indent=2), encoding="utf-8")

    summary_path = output_dir / "threshold_recalibration_results.txt"
    with summary_path.open("w", encoding="utf-8") as handle:
        handle.write("Threshold Recalibration Results\n")
        handle.write("================================\n\n")
        handle.write(f"Data paths: {', '.join(args.data_paths)}\n")
        handle.write(f"Ground truth: {args.ground_truth}\n")
        handle.write(f"Sample size: {len(eval_df)}\n")
        handle.write(f"ROC AUC: {roc_auc:.4f}\n\n")
        handle.write("Best threshold by F1 score\n")
        handle.write(f"  Threshold: {optimal_threshold:.2f}\n")
        handle.write(f"  Precision: {best_metrics['precision']:.4f}\n")
        handle.write(f"  Recall: {best_metrics['recall']:.4f}\n")
        handle.write(f"  F1 score: {best_metrics['f1_score']:.4f}\n")
        handle.write("\nReusable detector configuration\n")
        handle.write(f"  Config path: {detector_config_path}\n")
        handle.write(
            "  Applies recalibrated behavior_score_threshold directly; "
            "anomalous_score_threshold is kept at least as high to preserve category ordering.\n"
        )
        handle.write("  Use with: python run_pipeline.py --detector-config output/detector_config_recalibrated.json ...\n")

    print(f"Processed {len(eval_df)} labelled interviews")
    print(f"Best threshold: {optimal_threshold:.2f}")
    print(
        f"Precision={best_metrics['precision']:.4f} "
        f"Recall={best_metrics['recall']:.4f} "
        f"F1={best_metrics['f1_score']:.4f}"
    )
    print(f"ROC AUC: {roc_auc:.4f}")
    print(f"Saved threshold curve to: {threshold_path}")
    print(f"Saved ROC curve to: {roc_path}")
    print(f"Saved reusable detector config to: {detector_config_path}")
    print(f"Saved summary to: {summary_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
