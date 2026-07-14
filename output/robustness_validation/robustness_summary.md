# Robustness Validation Results

Date: 14 July 2026
Test suite at time of run: 33/33 passing
Reproduce this entire round with: `python scripts/run_robustness_validation.py`

## Why these experiments exist

Earlier validation runs scored precision 1.00 and recall 1.00 on every dataset. Scores that perfect usually mean the test is too easy, not that the detector is flawless. Three things were changed before this round to remove any advantage the detector had over the synthetic data:

1. **The generator now produces more realistic logs.** Interviews open with a form-start row and close with a form-end row (blank node, like real exports). Genuine respondents get per-question response times scaled by a fixed complexity profile (short demographic items, long health recall items), occasionally trip validation constraints, and navigate back at random positions. Fabricated and speeding profiles deliberately ignore question complexity, because complexity-blind uniform pacing is the fabrication signature reported by Wenz et al.
2. **Generator-specific tuning was removed from the detector.** The rule that suppressed the moderate back-navigation flag unless a long pause co-occurred is gone. The fixed 280,000 ms pause constant and the fixed pause-count minimum moved into the detector configuration. One rule was added: mean inter-question pause at or above 2.5 times the sample median raises a disengagement flag. The threshold is relative to each dataset's own median, so it carries no assumption about absolute pause lengths.
3. **Two defects found in code review were fixed.** The controller's hierarchical integrity flag was being overwritten by the detector (it is now preserved), and section statistics no longer include administrative form-start/form-end events, which previously created a pseudo-section whose "pause" spanned the entire interview and drowned the real pause signal.

All evaluation below uses seeds (7, 99) that were never used to develop or calibrate anything. Detector settings are the defaults; nothing was fitted to these datasets.

## Results

Success criteria from the proposal: precision >= 0.80, recall >= 0.75.

### Class-imbalance sweep (n=500, seed 7, canonical difficulty, SurveyCTO)

| Anomaly ratio | Precision | Recall | F1 |
|---|---|---|---|
| 5% | 0.9615 | 1.0000 | 0.9804 |
| 10% | 1.0000 | 1.0000 | 1.0000 |
| 20% | 1.0000 | 1.0000 | 1.0000 |
| 30% | 1.0000 | 1.0000 | 1.0000 |

At 5% prevalence one normal interview is falsely flagged. Precision is sensitive to prevalence, as expected: with few true anomalies, a single false positive costs almost four points of precision.

### Stress difficulty, held-out seeds (n=500, 20% anomalies)

Stress data overlaps the profiles on purpose: some genuine respondents are fast with no back-navigation, some fabricated interviews are only mildly compressed.

| Dataset | Precision | Recall | F1 |
|---|---|---|---|
| Seed 7, SurveyCTO | 0.9770 | 0.8500 | 0.9091 |
| Seed 7, ODK | 0.9570 | 0.8900 | 0.9223 |
| Seed 99, SurveyCTO | 1.0000 | 0.8800 | 0.9362 |
| Seed 99, ODK | 1.0000 | 0.8400 | 0.9130 |

All runs pass both success criteria. Detection by anomaly type (seed 99, SurveyCTO):

| Type | Detected | Rate |
|---|---|---|
| Speeding | 33/33 | 1.00 |
| Disengaged | 30/34 | 0.88 |
| Fabricated | 25/33 | 0.76 |

Aggregated across all four stress runs: speeding 132/132 (1.00), disengaged 121/136 (0.89), fabricated 93/132 (0.70), with per-run fabricated rates between 0.61 and 0.76.

### What the misses are

The undetected fabricated interviews come from the stress generator's "mildly compressed" variant (mean around 3,800 ms with moderate spread and one or two back-navigations). Univariate statistics barely separate these from a quick but genuine respondent. This is the known limitation of feature-by-feature IQR detection acknowledged in the proposal: anomalies that are only visible in joint patterns require multivariate methods, which were placed out of scope.

### Canonical suite (regression check)

The 24-interview canonical suite and the n=500 seed-42 benchmarks still score precision 1.00 and recall 1.00 in both formats after all changes.

## Files

- Metrics per run: `metrics_sweep_r*.csv`, `metrics_stress_seed*.csv`, `metrics_benchmark_n500_*.csv` in this directory
- Per-type detection: `detection_by_type_*.csv`
- Full predictions and feature datasets per run alongside the metrics files
- Generator datasets: `data/robustness_checks/` (regenerable with `tests/generate_benchmark_datasets.py`, seeds and ratios recorded in each `dataset_summary.json`)
