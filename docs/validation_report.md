# SKACE-Time-Data Validation Report

This document describes the current validation path used by the live pipeline.
The previous version of this report mixed older metrics and stale artifacts; it
has been replaced with a reproducible, dataset-aware summary.

## 0. Authoritative Results (July 2026 robustness round)

The most rigorous evaluation to date uses held-out seeds never touched during
development, a stress difficulty with overlapping profiles, and a class
imbalance sweep. Headline numbers: precision 0.96 to 1.00 and recall 0.84 to
1.00 across all runs, above the proposal thresholds of 0.80 and 0.75. Per-type
detection on stress data: speeding 1.00, disengaged 0.88, fabricated 0.76.
Methodology and full tables: `output/robustness_validation/robustness_summary.md`.
The sections below describe the standing validation workflow that preceded and
still complements that round.

## 1. Canonical Validation Set

The canonical labelled validation run is based on synthetic, ground-truth-backed
validation data. In the default full workflow, these files are generated into:
- `data/workflow_validation/canonical_validation/odk.csv`
- `data/workflow_validation/canonical_validation/surveycto.csv`
- `data/workflow_validation/canonical_validation/ground_truth_labels.csv`

Run command:

```bash
python run_pipeline.py \
  --inputs data/workflow_validation/canonical_validation/odk.csv data/workflow_validation/canonical_validation/surveycto.csv \
  --parser auto \
  --output-dir output \
  --label canonical_validation \
  --ground-truth data/workflow_validation/canonical_validation/ground_truth_labels.csv
```

Current verified result:
- Precision: `1.0000`
- Recall: `1.0000`
- F1-score: `1.0000`

The run writes:
- `output/question_features_canonical_validation.csv`
- `output/section_features_canonical_validation.csv`
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
python scripts/analyze_pipeline_metrics.py --datasets n500 n2000 n10000 --formats surveycto --output-dir output
```

Cross-format ODK spot-check:

```bash
python scripts/analyze_pipeline_metrics.py --datasets n500 --formats odk --output-dir output
```

The authoritative aggregate outputs are:
- `output/synthetic_dataset_metrics.csv`
- `output/synthetic_dataset_metrics.md`
- `output/synthetic_detection_by_type.csv`

## 3. Fresh Production-Readiness Sweep

To ensure the detector still meets the proposal contract on newly generated
datasets, run:

```bash
python scripts/validate_production_readiness.py --sizes 120 500 --seeds 11 42 --formats surveycto odk
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

## 4. Stress Validation

The canonical synthetic profiles are intentionally clean and reproducible, so
they are useful as a contract test but should not be treated as proof of real
field performance. A stricter stress mode now generates overlapping normal and
anomalous behavior so the detector can be evaluated against borderline cases:

```bash
python scripts/validate_production_readiness.py --sizes 500 --seeds 11 42 --formats surveycto odk --difficulty stress --data-root data/stress_benchmarks --output-dir output/stress_validation
```

The latest small stress sweep (`n120`, seeds `11` and `42`, SurveyCTO and ODK)
showed precision `1.0000` and recall between `0.7917` and `0.9583`. This means
the detector still clears the proposal's precision and recall targets under a
harder overlapping-data scenario.

The stress sweep is still not treated as a strict contract pass. Some subtle
fabricated interviews are detected as `REVIEW` rather than scoring `5` or higher,
and a few intentionally borderline anomalies remain `CLEAN`. That is useful
evidence rather than a defect in the report: the canonical dataset verifies the
proposal contract, while stress mode shows where real-world robustness still has
limits.

## 5. Baselines

The evaluation methodology in the proposal compares the full detector against:
- a duration-only IQR baseline
- a zero-back-navigation baseline

These baselines are now recomputed explicitly inside `strict_examiner_audit.py`
so the comparison can be reproduced from the raw files, generated features, and
ground-truth labels without manual spreadsheet work.

## 6. Recommended Reproducibility Commands

For the full workflow:

```bash
python scripts/run_complete_workflow.py
```

This command generates its own labelled validation bundle and does not need to
overwrite user-supplied files under `data/`.

For the strict end-to-end audit:

```bash
python scripts/strict_examiner_audit.py
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
