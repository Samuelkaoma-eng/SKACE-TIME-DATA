# SKACE-Time-Data Validation Report

**Project:** Automated Extraction and Analysis of Timing-Based Paradata Features for Survey Quality Assurance  
**Student:** Samuel Kaoma (2022016530) · **Course:** CSC 4004 · **Supervisor:** Mr. Mofya Phiri  
**Repository:** https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA  

This document reports the validation results and describes the path that produces
them: the datasets, the commands that reproduce every figure, and the acceptance
criteria each run is held to. Every number below is taken from a file in
`output/`, and the source file is named alongside it.

## 0. Headline results

The authoritative evaluation is the July 2026 robustness round. It uses seeds
that were never touched during development, a stress difficulty in which normal
and anomalous profiles overlap by construction, and a class imbalance sweep.
Detector settings are the defaults, with nothing fitted to the evaluated data.

| Measure | Result | Proposal threshold |
|---|---|---|
| Precision, across all runs | 0.96 to 1.00 | 0.80 |
| Recall, across all runs | 0.84 to 1.00 | 0.75 |

The lowest single precision observed is 0.9570, on seed 7 in ODK format at
stress difficulty. The lowest recall is 0.84, on seed 99 in ODK format.

Per-class recall by anomaly type. Each figure is the recall for that injected
class, that is the proportion of interviews of that type which the detector
flagged, aggregated across all four stress runs rather than quoted from any
single run. These are diagnostic breakdowns of the combined detector's recall,
not separate detectors and not separate success criteria.

| Anomaly type | Detected | Per-class recall | Per-run range |
|---|---|---|---|
| Speeding | 132 of 132 | 1.00 | 1.00 to 1.00 |
| Disengaged | 121 of 136 | 0.89 | 0.82 to 0.94 |
| Fabricated | 93 of 132 | 0.70 | 0.61 to 0.76 |

The proposal's success criteria, precision at or above 0.80 and recall at or
above 0.75, are defined for the combined detector and are met on every run with
margin, as the table above shows. No committed target is missed. The per-class
figures below that threshold, in particular fabricated recall at 0.70, are
reported because they locate where the method is weakest, not because they
breach a commitment.

Fabrication is the weakest of the three and is discussed in section 5. The
entire round is reproducible with one command, which regenerates its datasets
from recorded seeds and evaluates every condition:

```bash
python scripts/run_robustness_validation.py
```

Methodology and full tables: `output/robustness_validation/robustness_summary.md`.

## 1. Feature validity and effect sizes

Each of the 40 catalogued features was tested for its ability to separate normal
from anomalous interviews, using Mann-Whitney U on the n500 SurveyCTO benchmark
(400 normal, 100 anomalous) at alpha 0.05, with p-values adjusted for multiple
comparisons. Cohen's d is the primary effect size, with a rank-biserial
correlation derived from Mann-Whitney U reported alongside it.

**30 of the 40 features are significant.** The largest effects are concentrated
in the statistical and timing families:

| Feature | Cohen's d | Adjusted p |
|---|---|---|
| T-03 response time entropy | -10.57 | 1.6e-52 |
| Q-10 first to last interaction duration | -4.14 | 3.0e-52 |
| T-06 response time mean | -4.14 | 3.0e-52 |
| S-01 mean section pace | -4.14 | 3.0e-52 |
| Q-01 response time | -4.14 | 3.0e-52 |
| S-02 section duration | -3.80 | 8.2e-52 |
| V-01 total interview duration | -3.79 | 1.1e-51 |
| V-09 session length vs median | -3.79 | 1.1e-51 |
| T-02 response time IQR | -3.51 | 2.0e-52 |
| T-01 response time variance | -1.87 | 2.0e-52 |

The ten features that do not discriminate are V-07 time of day, V-08 day of
week, S-04 section to section pace ratio, S-05 and S-06 pause counts, S-09
section back navigation count, S-10 section completion rate, and Q-04 to Q-06
revisit flag, revisit count and field completion ratio. The first two are
contextual rather than behavioural. The remainder are constant across the
synthetic corpus and therefore carry no signal in it. All ten are retained in
the output for analysts but carry no weight in detection.

Full table, including rank-biserial values, group means and standard deviations:
`output/feature_validation_results.csv` and `output/feature_validation_results.txt`.

## 2. Baseline comparison

The proposal requires the full detector to be compared against two methods
representing current practice. Both baselines are recomputed from the raw files,
the generated features and the ground truth labels inside
`scripts/strict_examiner_audit.py`, so the comparison needs no manual work.

On the n500 SurveyCTO benchmark, 100 anomalies in 500 interviews:

| Method | Precision | Recall | F1 |
|---|---|---|---|
| Full detector | 1.0000 | 1.0000 | 1.0000 |
| Duration-only IQR baseline | 0.9565 | 0.6600 | 0.7811 |
| Zero back navigation baseline | 0.4648 | 0.6600 | 0.5455 |

The duration-only baseline reaches acceptable precision but misses 34 of the 100
anomalies, every one of which has a total duration inside the Tukey fences. The
zero back navigation baseline flags 142 interviews to find the same 66, giving
76 false positives. Neither baseline meets the proposal's recall threshold of
0.75. This is the central result of the project: aggregate duration alone misses
about a third of the injected anomalies that multi-feature analysis captures.

Source: `output/examiner_audit/strict_examiner_audit_report.md`.

## 3. Canonical validation set

The canonical labelled run is the contract test. It uses clean, reproducible
profiles and is deliberately easy, so it verifies the intended mapping between
profile and category rather than proving field performance.

```bash
python run_pipeline.py \
  --inputs data/workflow_validation/canonical_validation/odk.csv data/workflow_validation/canonical_validation/surveycto.csv \
  --parser auto \
  --output-dir output \
  --label canonical_validation \
  --ground-truth data/workflow_validation/canonical_validation/ground_truth_labels.csv
```

Verified result: precision 1.0000, recall 1.0000, F1 1.0000.

The run writes `output/question_features_canonical_validation.csv`,
`output/section_features_canonical_validation.csv`,
`output/feature_dataset_canonical_validation.csv`,
`output/anomaly_report_canonical_validation.csv`,
`output/pipeline_output_canonical_validation.csv`,
`output/predictions_canonical_validation.csv` and
`output/metrics_canonical_validation.{csv,json,md}`.

## 4. Class imbalance sweep

Held-out seed 7, canonical difficulty, SurveyCTO, 500 interviews, with the
proportion of anomalies varied.

| Anomaly prevalence | Precision | Recall | F1 |
|---|---|---|---|
| 5 percent | 0.9615 | 1.0000 | 0.9804 |
| 10 percent | 1.0000 | 1.0000 | 1.0000 |
| 20 percent | 1.0000 | 1.0000 | 1.0000 |
| 30 percent | 1.0000 | 1.0000 | 1.0000 |

Recall holds at 1.00 throughout. Precision falls only at 5 percent prevalence,
where a single false positive among few true anomalies costs almost four points.
This is a property of the metric rather than of the detector, but it matters
operationally, because real fabrication rates are usually low and the figure
quantifies the review burden a deployment should expect.

Source: `output/robustness_validation/metrics_sweep_r*.csv`.

## 5. Held-out stress evaluation

The stress generator overlaps the profiles on purpose. Some genuine respondents
are fast with no back navigation, and some fabricated interviews are only mildly
compressed. Seeds 7 and 99 were never used to develop or calibrate anything.

| Dataset | Precision | Recall | F1 |
|---|---|---|---|
| Seed 7, SurveyCTO | 0.9770 | 0.8500 | 0.9091 |
| Seed 7, ODK | 0.9570 | 0.8900 | 0.9223 |
| Seed 99, SurveyCTO | 1.0000 | 0.8800 | 0.9362 |
| Seed 99, ODK | 1.0000 | 0.8400 | 0.9130 |

All four runs clear both success criteria, and performance is consistent across
the two platform formats. That consistency is itself a result: the same detector,
unmodified, performs equivalently on structurally different inputs, which is what
the common intermediate representation was designed to achieve.

Per-class recall by anomaly type, all four runs. Each cell is the count of that
injected class the detector flagged, over the count present:

| Run | Speeding | Disengaged | Fabricated |
|---|---|---|---|
| Seed 7, SurveyCTO | 33/33 | 28/34 | 24/33 |
| Seed 7, ODK | 33/33 | 32/34 | 24/33 |
| Seed 99, SurveyCTO | 33/33 | 30/34 | 25/33 |
| Seed 99, ODK | 33/33 | 31/34 | 20/33 |
| **Aggregate** | **132/132 (1.00)** | **121/136 (0.89)** | **93/132 (0.70)** |

### What the misses are

All 39 undetected fabricated interviews come from the stress generator's mildly
compressed variant: mean response time around 3,800 ms, moderate spread, one or
two back navigations. Feature by feature these are almost indistinguishable from
a quick but genuine respondent. Their signature exists only in the joint pattern
of moderate compression, complexity-blind pacing and low navigation, which
univariate fences cannot capture. This is the known limitation of feature by
feature IQR detection acknowledged in the proposal, where multivariate methods
were placed out of scope.

Source: `output/robustness_validation/metrics_stress_seed*.csv` and
`detection_by_type_stress_seed*.csv`.

## 6. Earlier stress sweep, seeds 11 and 42

A separate stress sweep on seeds 11 and 42 predates the held-out round and is
retained for continuity. It is not the authoritative result; section 5 is.

```bash
python scripts/validate_production_readiness.py --sizes 500 --seeds 11 42 --formats surveycto odk --difficulty stress --data-root data/stress_benchmarks --output-dir output/stress_validation
```

It shows precision between 0.9770 and 0.9890 and recall between 0.8000 and
0.9000, clearing both thresholds. It does not pass the strict score contract:
some subtle fabricated interviews score as REVIEW rather than reaching 5, and a
few intentionally borderline anomalies remain CLEAN. The canonical datasets
verify the proposal contract; stress mode maps where robustness has limits.

Source: `output/stress_validation/production_readiness_summary.md`.

## 7. Larger benchmark packs and scale

Labelled synthetic packs live in `data/synthetic_datasets/n500`, `n2000` and
`n10000`.

```bash
python scripts/analyze_pipeline_metrics.py --datasets n500 n2000 n10000 --formats surveycto --output-dir output
```

Cross-format spot-check:

```bash
python scripts/analyze_pipeline_metrics.py --datasets n500 --formats odk --output-dir output
```

Cross-format parity at n500 is exact: SurveyCTO 1.0000/1.0000 and ODK
1.0000/1.0000. Scaling from 500 to 10,000 interviews, precision moves from
1.0000 to 0.9945 and recall holds at 1.0000, with runtime rising by a factor of
19.05 for a twentyfold increase in data, which is consistent with the near-linear
complexity the design targets.

Aggregate outputs: `output/synthetic_dataset_metrics.csv`,
`output/synthetic_dataset_metrics.md`, `output/synthetic_detection_by_type.csv`.

## 8. Production readiness sweep

To confirm the detector still meets the proposal contract on newly generated
data:

```bash
python scripts/validate_production_readiness.py --sizes 120 500 --seeds 11 42 --formats surveycto odk
```

Each run is checked against precision at or above 0.80, recall at or above 0.75,
fabricated interviews scoring at least 5, and normal interviews scoring at most
1. Summaries are written to
`output/production_validation/production_readiness_summary.{csv,json,md}`.

## 9. Reproducibility

Full workflow, which generates its own labelled validation bundle and does not
overwrite user-supplied files under `data/`:

```bash
python scripts/run_complete_workflow.py
```

Strict end-to-end audit:

```bash
python scripts/strict_examiner_audit.py
```

The examiner audit checks raw-format consistency against the format guide, CIR
normalisation, manual recalculation of selected features, anomaly score
reconstruction, reproducibility of precision and recall from ground truth,
fabricated versus normal feature separation, baseline comparisons, SurveyCTO and
ODK parity, and scale behaviour between n500 and n10000. Every check passes in
the recorded run.

Test suite: 33 tests, all passing, verified on Python 3.14.0 with pandas 3.0.1.

```bash
python -m pytest
```
