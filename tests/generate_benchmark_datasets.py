import argparse
import json
from pathlib import Path

from tests.test_adversarial import AdversarialDataGenerator


def build_dataset(dataset_size: int, seed: int, anomaly_ratio: float, output_dir: Path) -> dict:
    generator = AdversarialDataGenerator(seed=seed)
    plan = generator.build_benchmark_plan(dataset_size=dataset_size, anomaly_ratio=anomaly_ratio)

    surveycto_df = generator.generate_benchmark_suite(plan=plan, is_odk=False)
    odk_df = generator.generate_benchmark_suite(plan=plan, is_odk=True)
    ground_truth_df = generator.build_ground_truth_from_plan(plan)

    output_dir.mkdir(parents=True, exist_ok=True)
    surveycto_path = output_dir / "audit_logs_surveycto.csv"
    odk_path = output_dir / "audit_logs_odk.csv"
    ground_truth_path = output_dir / "ground_truth_labels.csv"
    summary_path = output_dir / "dataset_summary.json"

    surveycto_df.to_csv(surveycto_path, index=False)
    odk_df.to_csv(odk_path, index=False)
    ground_truth_df.to_csv(ground_truth_path, index=False)

    summary = {
        "dataset_size": int(dataset_size),
        "anomaly_ratio": float(anomaly_ratio),
        "seed": int(seed),
        "n_normal": int((ground_truth_df["anomaly_type"] == "normal").sum()),
        "n_fabricated": int((ground_truth_df["anomaly_type"] == "fabricated").sum()),
        "n_speeding": int((ground_truth_df["anomaly_type"] == "speeding").sum()),
        "n_disengaged": int((ground_truth_df["anomaly_type"] == "disengaged").sum()),
        "surveycto_rows": int(len(surveycto_df)),
        "odk_rows": int(len(odk_df)),
    }
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    return {
        "surveycto_path": str(surveycto_path),
        "odk_path": str(odk_path),
        "ground_truth_path": str(ground_truth_path),
        "summary_path": str(summary_path),
        "summary": summary,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate labelled synthetic benchmark datasets.")
    parser.add_argument("--dataset-size", type=int, required=True, help="Number of interviews to generate.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")
    parser.add_argument("--anomaly-ratio", type=float, default=0.2, help="Share of anomalous interviews.")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where audit_logs_surveycto.csv, audit_logs_odk.csv, and ground_truth_labels.csv will be written.",
    )
    args = parser.parse_args()

    results = build_dataset(
        dataset_size=args.dataset_size,
        seed=args.seed,
        anomaly_ratio=args.anomaly_ratio,
        output_dir=Path(args.output_dir),
    )

    print("Synthetic benchmark dataset generated.")
    print(f"  SurveyCTO: {results['surveycto_path']}")
    print(f"  ODK:       {results['odk_path']}")
    print(f"  Labels:    {results['ground_truth_path']}")
    print(f"  Summary:   {results['summary_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
