# SKACE-Time-Data Validation Report

**Project:** Automated Extraction and Analysis of Timing-Based Paradata
Features for Survey Quality Assurance  
**Student:** Samuel Kaoma, student number 2022016530  
**Course:** CSC 4004  
**Supervisor:** Mr. Mofya Phiri  
**Repository:** https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA  
**Validated state:** tag `v-resubmission`. The earlier tag `v-validation-complete` predates the September 2026 revision

---

This document reports the validation results and describes the path that
produces them: the datasets, the commands that reproduce every figure, and the
acceptance criteria each run is held to. Every number below is taken from a file
in `output/`, and the source file is named alongside it.

**Conventions.** Precision, recall and F1 are quoted to four decimal places in
tables and rounded to two in prose. Counts are exact. Runtimes are wall clock
seconds for a single named run, and the run is always named.

### Contents

| Section | Subject |
|---|---|
| [0](#0-headline-results) | Headline results and per-class recall |
| [0.1](#01-auditable-evidence) | Auditable evidence: tags, tests, coverage, confusion counts |
| [1](#1-feature-validity-and-effect-sizes) | Feature validity and effect sizes |
| [2](#2-baseline-comparison) | Baseline comparison |
| [2.1](#21-contribution-of-each-detection-component) | Contribution of each detection component |
| [3](#3-canonical-validation-set) | Canonical validation set |
| [4](#4-class-imbalance-sweep) | Class imbalance sweep |
| [4.1](#41-prevalence-envelope-beyond-thirty-percent) | Prevalence envelope beyond thirty percent |
| [5](#5-held-out-stress-evaluation) | Held-out stress evaluation and the fabrication shortfall |
| [6](#6-earlier-stress-sweep-seeds-11-and-42) | Earlier stress sweep, retained for continuity |
| [7](#7-larger-benchmark-packs-and-scale) | Larger benchmark packs and scale |
| [8](#8-production-readiness-sweep) | Production readiness sweep |
| [9](#9-reproducibility) | Reproducibility |

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
margin, as the table above shows. No committed target is missed within the
prevalence range the round tests.

**Operating envelope.** The method assumes that anomalies are a minority of the
batch, because its adaptive thresholds are estimated from the batch they judge.
Both criteria hold at every prevalence up to fifty percent; when anomalies are
the majority, recall under stress falls to 0.44 and precision to 0.73 (section
4.1). The detector should be run on batches pooled across enumerators rather
than on one enumerator's caseload alone. The per-class
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

## 0.1 Auditable evidence

**Validated state.** Tag `v-resubmission`. The exact commit it resolves to is
verifiable with:

```bash
git rev-parse v-resubmission
```

The tag table at the end of `docs/evidence_index.md` records the same mapping
and what is present in that tree.

**Test suite.** Command and output, run on Python 3.14.0:

```
$ python -m pytest -q
............................................                             [100%]
44 passed in 6.93s
```

**Feature coverage.** `docs/feature_coverage.md` tabulates all 40 catalogued
features across the Q, S, V and T families, showing where each is implemented,
whether the pipeline exported it in the recorded canonical run, and how it is
covered by tests. Summary: 40 of 40 implemented, 40 of 40 exported, 34 of 40
covered by a direct feature-naming test, 40 of 40 exercised end to end. Every one of the 30 features the validity analysis found significant now has a direct test; the six without one are constant across the synthetic corpus. The
table is regenerated by `python scripts/build_feature_coverage.py` rather than
maintained by hand.

**Granular outputs.** The question-level export carries all ten Q features, the
section-level export all ten S features, and the interview-level feature dataset
all forty, ten in each of the four families. Survey-level (V) and statistical
(T) outputs are complete.

**Confusion counts, per run.**

| Run | Format | TP | FN | FP | TN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|---|
| `benchmark_n500_odk` | ODK | 100 | 0 | 0 | 400 | 1.0000 | 1.0000 | 1.0000 |
| `benchmark_n500_surveycto` | SurveyCTO | 100 | 0 | 0 | 400 | 1.0000 | 1.0000 | 1.0000 |
| `stress_seed7_odk` | ODK | 89 | 11 | 4 | 396 | 0.9570 | 0.8900 | 0.9223 |
| `stress_seed7_surveycto` | SurveyCTO | 85 | 15 | 2 | 398 | 0.9770 | 0.8500 | 0.9091 |
| `stress_seed99_odk` | ODK | 84 | 16 | 0 | 400 | 1.0000 | 0.8400 | 0.9130 |
| `stress_seed99_surveycto` | SurveyCTO | 88 | 12 | 0 | 400 | 1.0000 | 0.8800 | 0.9362 |
| `sweep_r005` | SurveyCTO | 25 | 0 | 1 | 474 | 0.9615 | 1.0000 | 0.9804 |
| `sweep_r010` | SurveyCTO | 50 | 0 | 0 | 450 | 1.0000 | 1.0000 | 1.0000 |
| `sweep_r020` | SurveyCTO | 100 | 0 | 0 | 400 | 1.0000 | 1.0000 | 1.0000 |
| `sweep_r030` | SurveyCTO | 150 | 0 | 0 | 350 | 1.0000 | 1.0000 | 1.0000 |

**Confusion counts, aggregated by platform format.**

| Format | TP | FN | FP | TN | Precision | Recall |
|---|---|---|---|---|---|---|
| ODK | 273 | 27 | 4 | 1,196 | 0.9856 | 0.9100 |
| SurveyCTO | 598 | 27 | 3 | 2,872 | 0.9950 | 0.9568 |

Both formats clear the proposal criteria. The round raised seven false positives,
four on ODK inputs and three on SurveyCTO inputs. The two rows are not a
like-for-like comparison: each format's files hold different generated
interviews, and the prevalence sweep was run in SurveyCTO format only. When one
generated history is written into both formats, the two parsers give identical
features, scores and categories for all 1,500 interviews
(`scripts/run_platform_parity.py`, `output/platform_parity/`), so the difference
above reflects the sampled interviews, not the parsers. An earlier version of
this document attributed it to ISO timestamp conversion; that explanation is
withdrawn.

**Per-class recall by anomaly type** is in section 0 above, and the diagnostic
behind the fabricated figure is `docs/fabricated_detection_diagnostic.md`.
**Baselines** are section 2, **effect sizes** section 1, and the
**class-imbalance sensitivity check** section 4.

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
synthetic corpus, for reasons in the implementation as well as the generator:
S-04 averages to one when sections are of equal size, S-09 matches only `back`
and `backward` while the generator emits `jump`, every canonical pause is under
1.2 s, the generator never returns to an earlier question, and every question
and section is always completed. The Mann-Whitney statistic for the seven fully
constant features is 20000.0 (400 × 100 / 2, every pair tied) with an undefined
p-value. All ten are retained in
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
| V-10 rule (a run of 20 or more events without back-navigation) | 0.4648 | 0.6600 | 0.5455 |

The duration-only baseline reaches acceptable precision but misses 34 of the 100
anomalies, every one of which has a total duration inside the Tukey fences. The
V-10 baseline, which flags any interview containing a run of twenty or more
consecutive events without a back or jump event (earlier versions of this
document called it a zero back-navigation baseline, which it is not), flags 142
interviews to find the same 66, giving 76 false positives. Neither baseline meets the proposal's recall threshold of
0.75. This is the central result of the project: aggregate duration alone misses
about a third of the injected anomalies that multi-feature analysis captures.

Source: `output/examiner_audit/strict_examiner_audit_report.md`.

Under the held-out stress condition the gap widens. Across the four stress runs
the duration-only baseline flags no anomalous interview at all (recall 0.0000 on
every run), and the V-10 rule reaches recall between 0.35 and 0.51 at precision
between 0.16 and 0.22, against the full detector's 0.9830 precision and 0.8650
recall in aggregate. Source: `output/robustness_validation/baseline_breakdown.csv`,
produced by `scripts/baseline_breakdown.py`.

## 2.1 Contribution of each detection component

The proposal requires separate performance breakdowns for the IQR-based
statistical component and the rule-based component, so that the contribution of
each can be assessed rather than only their combined effect.

The combined detector flags an interview when `anomaly_score` reaches the
behaviour threshold of 2, where `anomaly_score = min(iqr_flags, 1) + rule_flags`.
The IQR contribution is capped at one on purpose, so that several correlated
duration, mean and variance outliers arising from the same underlying timing
pattern are not counted repeatedly. That cap makes the threshold of 2 unreachable
for the IQR component alone, so each component is isolated as follows:

- **IQR only:** any IQR fence fired, `iqr_flags >= 1`.
- **Rules only:** `rule_flags >= 2`, the same threshold the combined detector
  applies, with the IQR contribution removed.
- **Combined:** the shipped detector, unchanged.

Aggregated over all ten runs of the robustness round:

| Component | Precision | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|
| Combined | 0.9920 | 0.9416 | 0.9662 | 871 | 7 | 54 |
| Rules only | 0.9988 | 0.9319 | 0.9642 | 862 | 1 | 63 |
| IQR only | 0.6628 | 0.6162 | 0.6387 | 570 | 290 | 355 |

Per run:

| Run | Combined P / R | Rules only P / R | IQR only P / R |
|---|---|---|---|
| `benchmark_n500_odk` | 1.0000 / 1.0000 | 1.0000 / 1.0000 | 0.8547 / 1.0000 |
| `benchmark_n500_surveycto` | 1.0000 / 1.0000 | 1.0000 / 1.0000 | 0.8929 / 1.0000 |
| `stress_seed7_odk` | 0.9570 / 0.8900 | 0.9884 / 0.8500 | 0.3784 / 0.2800 |
| `stress_seed7_surveycto` | 0.9770 / 0.8500 | 1.0000 / 0.8100 | 0.3158 / 0.2400 |
| `stress_seed99_odk` | 1.0000 / 0.8400 | 1.0000 / 0.8300 | 0.3167 / 0.1900 |
| `stress_seed99_surveycto` | 1.0000 / 0.8800 | 1.0000 / 0.8800 | 0.3200 / 0.2400 |
| `sweep_r005` | 0.9615 / 1.0000 | 1.0000 / 1.0000 | 0.4717 / 1.0000 |
| `sweep_r010` | 1.0000 / 1.0000 | 1.0000 / 1.0000 | 0.6667 / 1.0000 |
| `sweep_r020` | 1.0000 / 1.0000 | 1.0000 / 1.0000 | 0.9174 / 1.0000 |
| `sweep_r030` | 1.0000 / 1.0000 | 1.0000 / 1.0000 | 0.9174 / 0.6667 |

### What the breakdown shows

The rule layer carries the detection. On its own it reaches precision 0.9988 and
recall 0.9319, which is within a point of the combined detector on both measures.
The IQR layer on its own reaches precision 0.6628 and recall 0.6162, and under
the stress condition its recall falls to between 0.19 and 0.28.

Combining the two is nonetheless worth doing, but the margin is small and should
be stated as such: the combination recovers nine true positives that the rules
miss, lifting recall from 0.9319 to 0.9416, and costs six additional false
positives, moving precision from 0.9988 to 0.9920. That is the entire measured
contribution of the IQR component in the shipped configuration.

The IQR component also degrades in a specific and instructive way. Across the
class imbalance sweep its recall holds at 1.00 while anomalies make up 5, 10 and
20 percent of the sample, then falls to 0.6667 at 30 percent. This is masking:
the fences are estimated from a sample that contains the outliers they are meant
to isolate, so as contamination rises the quartiles move with it and the fences
stop reaching the anomalies. The same mechanism accounts for part of the
fabricated recall shortfall analysed in
`docs/fabricated_detection_diagnostic.md`, and it is a property of applying
unsupervised fences to contaminated data rather than a defect in the
implementation.

This breakdown is regenerated from the recorded predictions, not from a fresh
run, with:

```bash
python scripts/component_breakdown.py
```

Full per-run values including confusion counts:
`output/robustness_validation/component_breakdown.csv`.

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

## 4.1 Prevalence envelope beyond thirty percent

The sweep above stops at thirty percent. Extended to ninety percent, at both
difficulties and at 100 and 500 interviews, on held-out seeds 7 and 99 with the
default configuration, it shows the range of prevalence the method holds in. Results for 500
interviews, the two seeds pooled on confusion counts. Canonical recall is 1.0000
at every level, and stress speeding recall is 1.00 up to fifty percent, 0.97 at
sixty, 0.16 at seventy and 0.00 from eighty:

| Anomaly prevalence | Canonical precision | Stress precision | Stress recall | Stress fabricated recall |
|---|---|---|---|---|
| 5 percent | 0.9804 | 0.9615 | 1.0000 | 1.00 |
| 10 percent | 0.9901 | 0.9789 | 0.9300 | 0.94 |
| 20 percent | 0.9950 | 0.9886 | 0.8650 | 0.74 |
| 30 percent | 1.0000 | 0.9871 | 0.7633 | 0.41 |
| 40 percent | 1.0000 | 0.9969 | 0.7925 | 0.47 |
| 50 percent | 1.0000 | 0.9950 | 0.7980 | 0.48 |
| 60 percent | 0.9983 | 1.0000 | 0.7900 | 0.44 |
| 70 percent | 1.0000 | 0.9868 | 0.5329 | 0.45 |
| 80 percent | 0.8000 | 0.7324 | 0.4688 | 0.40 |
| 90 percent | 0.9009 | 0.8440 | 0.4389 | 0.32 |

Both criteria hold up to fifty percent in every condition, including the noisier
100-interview runs. Beyond that the median-relative rules and the interquartile
fences are estimated from a batch whose median is an anomalous interview. Under
stress at eighty percent speeding is no longer detected at all, because the
speeders set the median, while 68 of the 100 genuine interviews are flagged,
mostly for pauses long relative to that median. Under canonical difficulty at
eighty and ninety percent every interview is flagged, so precision equals the
prevalence. Mild fabrication degrades earlier: its per-class recall is 0.74 at
twenty percent and below 0.50 from thirty.

This matters most for an enumerator who fabricates an entire caseload.
Analysed alone, that caseload is almost wholly anomalous and largely
undetectable by this method, so batches should be pooled across enumerators.
Section 6.4 and section 8 of the report give the full reading, and Figure 3
there plots the curve.

```bash
python scripts/run_prevalence_envelope.py
```

Source: `output/prevalence_envelope/envelope_summary.csv` and
`envelope_summary.md`, which also holds the 100-interview results.

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

All undetected fabricated interviews come from the stress generator's mildly
compressed variant: mean response time around 3,800 ms, moderate spread, one or
two back navigations. The generator emits two fabricated profiles under stress
difficulty, and the tightly compressed one is detected without exception.

A bounded diagnostic pass on these false negatives, run on development seeds 11
and 42 and reported in `docs/fabricated_detection_diagnostic.md`, established
that they are **not** indistinguishable from genuine interviews. Response time
entropy separates the two populations completely on those datasets: the highest
fabricated entropy observed is 1.983 and the lowest genuine entropy is 2.039,
with no overlap. The misses arise from how the detector reads that feature
rather than from an absence of signal in it. Two mechanisms are responsible.
The behavioural entropy rule uses an absolute constant of 0.5, which is
calibrated to the tightly compressed profile and cannot fire for the mildly
compressed one. The entropy IQR fence is computed on a dataset containing 20
percent injected anomalies, which pulls the lower quartile down and the fence
with it, so it fires for a minority of the misses where a fence estimated from
genuine interviews alone would separate all of them.

A related structural point applies to the other statistical features. For
strongly right-skewed non-negative quantities such as response time variance and
IQR, the Tukey lower fence `Q1 - 1.5 x IQR` falls below zero and is therefore
unreachable, so no low-side outlier can be detected on those features at all.
Entropy is the exception because it is bounded and roughly symmetric.

This corrects an earlier explanation in this document, which attributed the
misses to a joint pattern that univariate methods cannot capture. The data does
not support that reading. No threshold was changed in producing the diagnostic
and the results reported above stand unaltered.

### The correction exists, and is off by default in the evaluated system

The diagnosis was acted on. A corrected entropy fence was developed on the same
development seeds, frozen, and evaluated once against the held-out data. It
keeps the absolute constant as a floor and adds a fence at the median minus three
times the distance from the median to the third quartile, taking its scale from
the upper half of the entropy distribution because every anomaly profile in scope
lowers entropy and none raises it. That half is less contaminated than the lower
half, not uncontaminated, since the anomalies still pull the median down. An
earlier version of this report said the fence reduces to the ordinary Tukey fence
for a symmetric distribution. It does not: under symmetry it equals a Tukey fence
with a multiplier of 1.0 rather than 1.5, so it is also tighter. Under that
correction, fabricated per-class recall rises from 0.70 to 1.00 and the lowest
precision observed anywhere in the round falls from 0.9570 to 0.8333.

The gain concentrates in the stress condition and the cost concentrates at low
prevalence, where recall was already complete and the extra flags fall entirely
on genuine interviews. Since realistic fabrication rates are low, the correction
as it stands buys no additional detection in the condition that most resembles
deployment and pays for it in false accusations. It therefore ships as a
configuration option that is off by default (`entropy_fence_scale`, unset), and
every figure in this document describes the detector with it off. Setting
`entropy_fence_scale` to 3.0 reproduces the held-out figures above exactly; the
full record is `docs/entropy_fence_change.md`.

The full trade-off, and the argument that adopting it is a deployment judgement
about the relative cost of an undetected fabrication against a genuine
enumerator sent for review rather than a methodological question, is set out in
section 7 of `report/final_academic_report.md`.

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

The smaller labelled synthetic packs live in `data/synthetic_datasets/n500` and
`n2000`. The larger `n10000` pack is regenerated from its recorded seed before
rerunning the scale check:

```bash
python tests/generate_benchmark_datasets.py --dataset-size 10000 --seed 42 --output-dir data/synthetic_datasets/n10000
```

```bash
python scripts/analyze_pipeline_metrics.py --datasets n500 n2000 n10000 --formats surveycto --output-dir output
```

Cross-format spot-check:

```bash
python scripts/analyze_pipeline_metrics.py --datasets n500 --formats odk --output-dir output
```

Cross-format parity at n500 is exact: SurveyCTO 1.0000/1.0000 and ODK
1.0000/1.0000. Scaling from 500 to 10,000 interviews, precision moves from
1.0000 to 0.9945 while recall holds at 1.0000.

### Source of the scaling figures

The runtime figures quoted here and in the final report are those of the strict
examiner audit, which is the run that carries the scale check as an explicit
pass or fail condition. Its raw times are:

| Dataset | Format | Interviews | Runtime | Precision | Recall |
|---|---|---|---|---|---|
| `n500` | SurveyCTO | 500 | 56.12 s | 1.0000 | 1.0000 |
| `n10000` | SurveyCTO | 10,000 | 1,068.87 s | 0.9945 | 1.0000 |

A twentyfold increase in input cost a factor of 19.05 in runtime on this run.
The factor moves between runs and machines (18.04 in a second run here, 20.3 to
21.0 in an independent reproduction on other hardware) and should not carry
weight; what holds throughout is a roughly constant cost per interview, about
0.11 s, which is the near-linear scaling the design targets.

Source: `output/examiner_audit/strict_examiner_audit_report.md` and its JSON
companion, in which the same two times appear as `n500_runtime_seconds` and
`n10000_runtime_seconds` under the scale stability check.

These are wall clock timings of one run and they move between runs on the same
machine. A separate aggregate timing file records 57.54 s and 1,037.74 s for the
same two datasets, a factor of 18.04, from a different run:
`output/synthetic_dataset_metrics.csv` and its JSON companion. The two pairs are
not one measurement reported twice and should not be read as such. The strict
examiner audit is the source cited throughout this document.

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

Test suite: 44 tests, all passing on Python 3.14.0 with pandas 3.0.1 from
`requirements-validated.txt`, and with pandas 2.3.2.

```bash
python -m pytest
```
