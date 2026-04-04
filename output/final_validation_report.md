# SKACE Final Validation Report

## Executive Summary

The pipeline has been revalidated after hardening the anomaly scoring and the
labelled evaluation workflow.

Verified benchmark results:

- Canonical 24-interview benchmark (`data/odk.csv` + `data/surveycto.csv`):
  precision `1.0000`, recall `1.0000`, F1 `1.0000`
- Checked-in synthetic benchmark packs:
  - `n500` SurveyCTO: precision `1.0000`, recall `1.0000`, F1 `1.0000`
  - `n500` ODK: precision `1.0000`, recall `1.0000`, F1 `1.0000`
  - `n2000` SurveyCTO: precision `1.0000`, recall `1.0000`, F1 `1.0000`
- Fresh generated production-readiness datasets:
  - `n120_seed11` SurveyCTO + ODK: full contract pass
  - `n120_seed42` SurveyCTO + ODK: full contract pass
  - `n500_seed11` SurveyCTO + ODK: full contract pass
  - `n500_seed42` SurveyCTO + ODK: full contract pass

For every verified synthetic dataset above, the acceptance contract holds:

- fabricated interviews score `>= 5`
- normal interviews score `<= 1`
- precision `>= 0.80`
- recall `>= 0.75`

## Output Contract

The pipeline now supports labelled evaluation directly from `run_pipeline.py`.
Each run writes:

- `output/feature_dataset_<label>.csv`
- `output/anomaly_report_<label>.csv`
- `output/pipeline_output_<label>.csv`

If `--ground-truth` is supplied, it also writes:

- `output/predictions_<label>.csv`
- `output/metrics_<label>.csv`
- `output/metrics_<label>.json`
- `output/metrics_<label>.md`

This means new labelled datasets no longer depend on the old hard-coded
benchmark scripts to obtain precision/recall.

## Production-Readiness Sweep

The repeated fresh-run validation is summarized in:

- `output/production_validation/production_readiness_summary.csv`
- `output/production_validation/production_readiness_summary.md`

Those files were generated from new synthetic datasets created in both
SurveyCTO and ODK formats, across multiple sizes and seeds, using:

- `tests/generate_benchmark_datasets.py`
- `validate_production_readiness.py`

## Remaining Caveat

The detector and output contract are now behaving consistently on the verified
datasets above, but the local `pytest` environment on this machine is still
affected by Windows filesystem permission issues around temporary/cache
directories. The pipeline logic is validated by direct execution, but the
pytest harness still needs environment cleanup before it can be treated as a
clean production test gate.
