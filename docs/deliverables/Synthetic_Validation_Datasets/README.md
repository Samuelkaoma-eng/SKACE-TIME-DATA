# Synthetic Validation Datasets

Deliverable 3 of the project proposal: labelled synthetic survey audit logs
with injected anomalies, in both SurveyCTO and ODK formats.

Each dataset directory contains:
- `audit_logs_surveycto.csv`: SurveyCTO-format audit log (epoch-millisecond timestamps)
- `audit_logs_odk.csv`: ODK-format audit log (ISO 8601 timestamps)
- `ground_truth_labels.csv`: per-interview anomaly type and binary label
- `dataset_summary.json`: recorded seed, size, anomaly ratio and difficulty

Datasets:

| Directory | Interviews | Anomaly ratio | Seed | Difficulty |
|---|---|---|---|---|
| `synthetic_datasets/n500` | 500 | 0.20 | 42 | canonical |
| `synthetic_datasets/n2000` | 2,000 | 0.20 | 42 | canonical |
| `synthetic_datasets/n10000` | 10,000 | 0.20 | 42 | canonical |

Every dataset is reproducible from the repository root, for example:

```bash
python tests/generate_benchmark_datasets.py --dataset-size 500 --seed 42 --output-dir data/synthetic_datasets/n500
```

This copy is identical to `data/synthetic_datasets/` in the repository. The
additional held-out evaluation datasets (imbalance sweep and stress difficulty,
seeds 7 and 99) are regenerated on demand by
`python scripts/run_robustness_validation.py`, with their parameters recorded
in the validation report.
