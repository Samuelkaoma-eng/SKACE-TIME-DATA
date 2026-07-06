from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


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
    ).copy()
    melted = melted.assign(dataset_format=melted["dataset"].astype(str) + " / " + melted["format"].astype(str))

    metric_order = ["precision", "recall", "f1_score", "accuracy"]
    dataset_labels = list(dict.fromkeys(melted["dataset_format"].tolist()))
    x_positions = list(range(len(dataset_labels)))
    bar_width = 0.18
    offsets = [-1.5 * bar_width, -0.5 * bar_width, 0.5 * bar_width, 1.5 * bar_width]
    colors = ["#0f766e", "#2563eb", "#d97706", "#7c3aed"]

    plt.figure(figsize=(12, 6))
    for metric, offset, color in zip(metric_order, offsets, colors):
        metric_values = []
        for label in dataset_labels:
            match = melted[(melted["dataset_format"] == label) & (melted["metric"] == metric)]["value"]
            metric_values.append(float(match.iloc[0]) if not match.empty else 0.0)
        plt.bar([x + offset for x in x_positions], metric_values, width=bar_width, label=metric, color=color)

    plt.ylim(0, 1.05)
    plt.xlabel("Dataset / Format")
    plt.ylabel("Score")
    plt.title("Synthetic Dataset Performance Metrics")
    plt.xticks(x_positions, dataset_labels, rotation=20, ha="right")
    plt.legend()
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


def create_detection_plot(type_df: pd.DataFrame, output_path: Path) -> None:
    plot_df = type_df.copy()
    plot_df = plot_df.assign(dataset_format=plot_df["dataset"].astype(str) + " / " + plot_df["format"].astype(str))

    anomaly_types = list(dict.fromkeys(plot_df["anomaly_type"].astype(str).tolist()))
    dataset_labels = list(dict.fromkeys(plot_df["dataset_format"].tolist()))
    x_positions = list(range(len(dataset_labels)))
    bar_width = 0.24 if anomaly_types else 0.24
    offsets = [((idx - (len(anomaly_types) - 1) / 2) * bar_width) for idx in range(len(anomaly_types))]
    colors = ["#ef4444", "#f59e0b", "#3b82f6", "#10b981"]

    plt.figure(figsize=(12, 6))
    for idx, anomaly_type in enumerate(anomaly_types):
        values = []
        for label in dataset_labels:
            match = plot_df[
                (plot_df["dataset_format"] == label) & (plot_df["anomaly_type"].astype(str) == anomaly_type)
            ]["detection_rate"]
            values.append(float(match.iloc[0]) if not match.empty else 0.0)
        plt.bar(
            [x + offsets[idx] for x in x_positions],
            values,
            width=bar_width,
            label=anomaly_type,
            color=colors[idx % len(colors)],
        )

    plt.ylim(0, 1.05)
    plt.xlabel("Dataset / Format")
    plt.ylabel("Detection Rate")
    plt.title("Detection Rate by Anomaly Type")
    plt.xticks(x_positions, dataset_labels, rotation=20, ha="right")
    if anomaly_types:
        plt.legend(title="Anomaly Type")
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


def main() -> int:
    plt.style.use("seaborn-v0_8-whitegrid")
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
