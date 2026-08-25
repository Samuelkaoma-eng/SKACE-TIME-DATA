# Diagnostic: Fabricated False Negatives

**Scope.** One bounded diagnostic pass on the fabricated interviews the detector
does not flag, requested by the supervisor for the Validation and documentation
milestone.

**Discipline.** All analysis below uses development seeds **11 and 42** only.
The held-out seeds 7 and 99, on which the reported results rest, were not opened
during this work. No threshold, rule or generator parameter was changed while
producing it. Any adjustment arising from this diagnostic is to be justified from
design or literature, frozen, and evaluated exactly once.

**Reproduce.** Four pipeline runs, two development seeds by two formats:

```bash
python run_pipeline.py \
  --inputs data/stress_benchmarks/n500_seed11/audit_logs_surveycto.csv \
  --ground-truth data/stress_benchmarks/n500_seed11/ground_truth_labels.csv \
  --label diag_seed11_surveycto --output-dir <scratch>
```

## 1. The stress generator emits two fabricated profiles

`tests/test_adversarial.py`, `_fabricated_interview`, branches under stress
difficulty:

| Variant | Response times | Back navigation | Share |
|---|---|---|---|
| A, tightly compressed | `N(1800, 180)`, clipped at 700 ms | none | 45 percent |
| B, mildly compressed | `N(3800, 650)`, clipped at 1200 ms | zero or one | 55 percent |

Ground truth records `anomaly_type` but not the variant, so interviews were
assigned by observed mean response time, splitting at 2800 ms, which lies
between the two modes with no overlap.

## 2. Every miss is variant B

| Variant | Present | Detected | Per-class recall |
|---|---|---|---|
| A, tightly compressed | 61 | 61 | **1.00** |
| B, mildly compressed | 71 | 35 | **0.49** |
| Both | 132 | 96 | 0.73 |

Variant A is caught without exception. The headline fabricated recall is
therefore not a uniform 0.70 difficulty: it is one profile detected perfectly
and another detected at about a coin toss.

Per-run, variant B recall is also unstable: 0.75 and 0.29 on seed 11, 0.20 and
0.73 on seed 42. That spread is wider than sampling noise on 15 to 21 cases
comfortably explains, which pointed at a threshold boundary rather than a
difficulty gradient.

## 3. Missed and caught variant B are the same population

Median feature values across the four runs:

| Group | n | T-06 mean RT | T-01 variance | T-02 IQR | T-03 entropy | V-01 duration |
|---|---|---|---|---|---|---|
| A caught | 61 | 1,796 | 30,881 | 220 | 0.47 | 42,426 |
| B missed | 36 | 3,891 | 472,811 | 882 | 1.54 | 83,910 |
| B caught | 35 | 3,677 | 404,837 | 799 | 1.44 | 79,996 |
| Normal | 1,600 | 8,140 | 19,600,118 | 4,876 | 3.25 | 175,960 |

Missed and caught variant B are indistinguishable from each other. Both sit
roughly forty times below normal on response time variance and less than half
of normal on entropy. Whatever separates caught from missed, it is not a
difference in the interviews.

## 4. Entropy separates the classes completely

| Group | Minimum | Median | Maximum |
|---|---|---|---|
| A caught | 0.000 | 0.469 | 0.934 |
| B caught | 1.054 | 1.441 | 1.983 |
| B missed | 0.993 | 1.544 | 1.776 |
| Normal | 2.039 | 3.246 | — |

The highest fabricated entropy observed is 1.983. The lowest normal entropy
observed is 2.039. There is a clean gap and no overlap. On these datasets a
single feature, response time entropy, separates every fabricated interview
from every genuine one.

The Tukey lower fence for entropy computed on genuine interviews alone is
**2.008**, which falls inside that gap. All 36 missed interviews lie below it.

## 5. Why the detector misses them anyway

Two independent reasons, both visible in the flags the missed interviews raise.

**The entropy rule uses an absolute constant.**
`src/validation/anomaly_detector.py` flags `T-03_rt_entropy < 0.5`. Variant A
has a maximum entropy of 0.934 and a median of 0.469, so the rule fires for it
routinely. Variant B has a minimum of 0.993, so the rule can never fire for it.
The constant is calibrated to the canonical fabricated profile, not to a
distributional property of the data.

**The entropy IQR fence is degraded by contamination.**
The `flag_iqr_entropy` rule computes its fence on the dataset being scored,
which contains 20 percent injected anomalies. Those anomalies pull the lower
quartile down, and the fence with them. It fires for only 5 of the 36 missed
interviews, against the clean-data fence of 2.008 which would separate all 36.
This is textbook masking in unsupervised outlier detection: the estimator is
computed from a sample that includes the outliers it is meant to find.

What the missed interviews actually raise:

| Group | Flags raised | Median score |
|---|---|---|
| A caught | 3 to 8, including `flag_low_entropy` | 7 |
| B caught | `flag_short_relative_duration` + `flag_low_mean_rt` | 2 |
| B missed | `flag_short_relative_duration` alone, 17 of 36 | 1 |

The caught and missed split inside variant B turns on whether the absolute mean
response time rule happens to fire. That is a threshold boundary effect, which
explains the run-to-run instability in section 2.

## 6. A further consequence for the Tukey fences

For the right-skewed non-negative features the lower Tukey fence is negative and
therefore unreachable by any interview:

| Feature | Lower fence, contaminated | Lower fence, genuine only |
|---|---|---|
| T-01 response time variance | -39,650,004 | -37,327,716 |
| T-02 response time IQR | -3,538 | -2,259 |
| T-06 mean response time | -1,722 | — |
| V-01 total duration | -27,635 | — |

Tukey's fences assume approximate symmetry. On strongly right-skewed
distributions such as response time variance, `Q1 - 1.5 x IQR` falls below zero,
so no low-side outlier can ever be detected on those features regardless of
contamination. Entropy is the exception because it is bounded and roughly
symmetric, which is precisely why it is the one feature with a usable fence.

## 7. What this means for the reported figures

The mechanism previously documented, that these interviews are indistinguishable
feature by feature and detectable only as a joint pattern, is **not supported by
the data**. A single univariate feature separates them with a clean margin. The
misses are a calibration and fence-construction issue, not evidence that
univariate detection is insufficient for this profile.

The reported results are unaffected. No threshold was changed, the held-out
evaluation stands as published, and the combined detector continues to exceed
the proposal criteria of precision 0.80 and recall 0.75 on every run. What
changes is the explanation attached to the fabricated recall figure, which was
wrong and is corrected here.

## 8. Candidate adjustment, not yet applied

Consistent with the earlier de-tuning round, which removed a fixed 280,000 ms
pause constant in favour of a rule relative to each dataset's own median, the
absolute entropy constant of 0.5 is the remaining hard-coded behavioural
threshold. Replacing it with a median-relative form would follow the design
precedent already set in this codebase and would address the mechanism in
section 5 without reference to any held-out result.

This has **not** been applied. Applying it would change every published figure
and require the full validation round, both reports and all deliverables to be
regenerated. That decision, and the single frozen evaluation that must follow
it, is deferred pending supervisor agreement.
