from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required input file not found: {path}")
    return pd.read_csv(path)


def create_metric_plot(metrics_df: pd.DataFrame, output_path: Path) -> None:
    melted = metrics_df.melt(
        id_vars=["dataset", "format"],
        value_vars=["precision", "recall", "f1_score", "accuracy"],
        var_name="metric",
        value_name="value",
    )
    melted["dataset_format"] = melted["dataset"] + " / " + melted["format"]

    plt.figure(figsize=(12, 6))
    sns.barplot(data=melted, x="dataset_format", y="value", hue="metric")
    plt.ylim(0, 1.05)
    plt.xlabel("Dataset / Format")
    plt.ylabel("Score")
    plt.title("Synthetic Dataset Performance Metrics")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


def create_detection_plot(type_df: pd.DataFrame, output_path: Path) -> None:
    type_df = type_df.copy()
    type_df["dataset_format"] = type_df["dataset"] + " / " + type_df["format"]

    plt.figure(figsize=(12, 6))
    sns.barplot(data=type_df, x="dataset_format", y="detection_rate", hue="anomaly_type")
    plt.ylim(0, 1.05)
    plt.xlabel("Dataset / Format")
    plt.ylabel("Detection Rate")
    plt.title("Detection Rate by Anomaly Type")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


def main() -> int:
    sns.set_theme(style="whitegrid")
    output_dir = Path("output")
    metrics_path = output_dir / "synthetic_dataset_metrics.csv"
    type_path = output_dir / "synthetic_detection_by_type.csv"

    metrics_df = load_csv(metrics_path)
    create_metric_plot(metrics_df, output_dir / "synthetic_metrics_overview.png")

    if type_path.exists():
        type_df = load_csv(type_path)
        if not type_df.empty:
            create_detection_plot(type_df, output_dir / "synthetic_detection_by_type.png")

    print(f"Saved metrics overview to: {output_dir / 'synthetic_metrics_overview.png'}")
    if type_path.exists():
        print(f"Saved detection overview to: {output_dir / 'synthetic_detection_by_type.png'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
