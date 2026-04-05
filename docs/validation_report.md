# SKACE-Time-Data Validation Report

This document describes the current validation path used by the live pipeline.
The previous version of this report mixed older metrics and stale artifacts; it
has been replaced with a reproducible, dataset-aware summary.

## 1. Canonical Validation Set

The canonical labelled validation run uses:
- `data/odk.csv`
- `data/surveycto.csv`
- `data/ground_truth_labels.csv`

Run command:

```bash
python run_pipeline.py \
  --inputs data/odk.csv data/surveycto.csv \
  --parser auto \
  --output-dir output \
  --label canonical_validation \
  --ground-truth data/ground_truth_labels.csv
```

Current verified result:
- Precision: `1.0000`
- Recall: `1.0000`
- F1-score: `1.0000`

The run writes:
- `output/feature_dataset_canonical_validation.csv`
- `output/anomaly_report_canonical_validation.csv`
- `output/pipeline_output_canonical_validation.csv`
- `output/predictions_canonical_validation.csv`
- `output/metrics_canonical_validation.{csv,json,md}`

## 2. Larger Synthetic Benchmark Packs

The project also validates on labelled synthetic benchmark packs in:
- `data/synthetic_datasets/n500`
- `data/synthetic_datasets/n2000`
- `data/synthetic_datasets/n10000`

Run command:

```bash
python analyze_pipeline_metrics.py --datasets n500 n2000 n10000 --formats surveycto --output-dir output
```

Cross-format ODK spot-check:

```bash
python analyze_pipeline_metrics.py --datasets n500 --formats odk --output-dir output
```

The authoritative aggregate outputs are:
- `output/synthetic_dataset_metrics.csv`
- `output/synthetic_dataset_metrics.md`
- `output/synthetic_detection_by_type.csv`

## 3. Fresh Production-Readiness Sweep

To ensure the detector still meets the proposal contract on newly generated
datasets, run:

```bash
python validate_production_readiness.py --sizes 120 500 --seeds 11 42 --formats surveycto odk
```

This sweep verifies that each run satisfies:
- precision `>= 0.80`
- recall `>= 0.75`
- fabricated interviews score `>= 5`
- normal interviews score `<= 1`

The summary outputs are:
- `output/production_validation/production_readiness_summary.csv`
- `output/production_validation/production_readiness_summary.json`
- `output/production_validation/production_readiness_summary.md`

## 4. Baselines

The evaluation methodology in the proposal compares the full detector against:
- a duration-only IQR baseline
- a zero-back-navigation baseline

These baselines are now recomputed explicitly inside `strict_examiner_audit.py`
so the comparison can be reproduced from the raw files, generated features, and
ground-truth labels without manual spreadsheet work.

## 5. Recommended Reproducibility Commands

For the full workflow:

```bash
python run_complete_workflow.py
```

For the strict end-to-end audit:

```bash
python strict_examiner_audit.py
```

The examiner audit checks:
- raw-format consistency against the format guide
- CIR normalization
- manual feature calculations for selected features
- anomaly score reconstruction
- reproducibility of precision/recall from ground truth
- fabricated-vs-normal feature separation
- baseline comparisons
- SurveyCTO/ODK parity
- scale behavior between `n500` and `n10000`
