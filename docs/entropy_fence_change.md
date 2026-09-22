# Change: distribution-relative entropy fence

This is the rule adjustment arising from `docs/fabricated_detection_diagnostic.md`,
prepared under the frozen-evaluation discipline agreed for it. It was developed on
the branch `fix/entropy-threshold-relative`, which was cut from a rewritten history
and shares no commit with `main`. The code has since been carried onto `main` as a
configuration option that is **off by default**, and the branch is preserved as the
tag `archive/entropy-fence`. Setting `entropy_fence_scale` to 3.0 in a detector
configuration file reproduces every held-out figure below exactly; leaving it unset
reproduces every figure in the report and the validation report.

Two claims in the original version of this note were wrong and are corrected below:
that the fence reduces to Tukey's under symmetry, and that the upper half of the
entropy distribution contains no anomalies.

## What the diagnostic established

Fabricated interviews the detector missed were not indistinguishable from genuine
ones. Response time entropy separated the two populations with no overlap on the
development datasets, the highest fabricated value being 1.983 against a lowest
genuine value of 2.039. The detector failed to act on that separation for two
reasons: the behavioural entropy rule compared against a fixed constant of 0.5,
calibrated to one of the two fabrication profiles the stress generator emits, and
the accompanying interquartile fence was estimated from a sample containing
twenty percent injected anomalies, which depressed the lower quartile and the
fence along with it.

## The change

The absolute constant is kept as a floor, so an interview with essentially no
variation in response time is still flagged whatever the surrounding dataset
looks like. Alongside it the rule now applies a fence estimated from the
less contaminated side of the distribution:

    fence = median - entropy_fence_scale * (Q3 - median)

with `entropy_fence_scale` set to 3.0 when the option is enabled (it defaults to
`None`, which disables the fence) and a minimum sample of 30 before the fence is
applied at all.

## Why this form and not another

Every anomaly profile in scope depresses entropy and none raises it, so the upper
half of the entropy distribution holds few anomalies. Estimating the scale from
that half alone therefore reduces the contamination that made the plain fence
ineffective. It does not remove it: the anomalies sit below the median and pull it
down, and if every anomaly lies below every genuine interview, twenty percent
contamination moves the sample median to the 37.5th percentile of the genuine
interviews. This is the masking problem in unsupervised outlier
detection, where the estimator is computed from a sample that includes the
outliers it is meant to isolate.

The fence does not reduce to Tukey's under symmetry, as this note first claimed.
For a symmetric distribution with `Q3 - median = d`, the interquartile range is
`2d`, so Tukey's lower fence is `Q1 - 1.5 * 2d = median - 4d`, while this fence is
`median - 3d`. It is tighter by `d`, equivalent under symmetry to a Tukey fence
with a multiplier of 1.0 rather than 1.5, so part of the additional detection and
part of the additional false positives reported below follow from the tighter
fence rather than from the change of scale estimate alone. The construction is the
lower-side form of the semi-interquartile fence discussed by Hubert and
Vandervieren (2008, section 1).

The choice follows the precedent already set in this project. The earlier
de-tuning round removed a fixed 280,000 ms pause constant in favour of a rule
relative to each dataset's own median, and `low_rt_iqr_median_ratio` and
`low_mean_rt_median_ratio` are both already relative. The entropy constant was
the last hard-coded behavioural threshold remaining.

No threshold was selected by comparing candidate values against results. The form
was derived from the contamination argument above, and the scale factor of 3.0 is
the constant of the semi-interquartile fence. It was believed at the time to make
the fence equivalent to the existing Tukey fence, which, as corrected above, it
does not.

## Development results, seeds 11 and 42

Held-out seeds 7 and 99 were not opened during development.

| Run | Precision | Recall | Fabricated recall |
|---|---|---|---|
| Seed 11, SurveyCTO | 0.9890 to 0.9600 | 0.9000 to 0.9600 | 28/33 to 33/33 |
| Seed 11, ODK | 0.9877 to 0.9794 | 0.8000 to 0.9500 | 18/33 to 33/33 |
| Seed 42, SurveyCTO | 0.9770 to 0.9798 | 0.8500 to 0.9700 | 21/33 to 33/33 |
| Seed 42, ODK | 0.9780 to 0.9300 | 0.8900 to 0.9300 | 29/33 to 33/33 |

Values are given as before to after. Fabricated recall moves from 96 of 132 to
132 of 132. False positives on genuine interviews move from 1, 1, 2 and 2 to 4,
2, 2 and 7 out of 400, so the recall gain is bought with a small and visible
precision cost. Every run remains above the proposal criteria of precision 0.80
and recall 0.75.

Test suite: 37 of 37 passing.

## Frozen state

The generator, the rules and the thresholds are frozen at the commit that adds
this file. The held-out evaluation on seeds 7 and 99 is run once against that
state, and its result is recorded below whatever it shows.

## Held-out result

Run once against the frozen state at commit `7cd5e24`, with
`python scripts/run_robustness_validation.py`. Recorded as it came out.

| Run | Difficulty | Precision before | Precision after | Recall before | Recall after |
|---|---|---|---|---|---|
| `sweep_r005` | canonical | 0.9615 | 0.8333 | 1.0000 | 1.0000 |
| `sweep_r010` | canonical | 1.0000 | 0.9804 | 1.0000 | 1.0000 |
| `sweep_r020` | canonical | 1.0000 | 0.9804 | 1.0000 | 1.0000 |
| `sweep_r030` | canonical | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `benchmark_n500_surveycto` | canonical | 1.0000 | 0.9804 | 1.0000 | 1.0000 |
| `benchmark_n500_odk` | canonical | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `stress_seed7_surveycto` | stress | 0.9770 | 0.9307 | 0.8500 | 0.9400 |
| `stress_seed7_odk` | stress | 0.9570 | 0.9074 | 0.8900 | 0.9800 |
| `stress_seed99_surveycto` | stress | 1.0000 | 0.9057 | 0.8800 | 0.9600 |
| `stress_seed99_odk` | stress | 1.0000 | 0.9700 | 0.8400 | 0.9700 |

Precision range moves from 0.9570 to 1.0000, down to 0.8333 to 1.0000. Recall
range moves from 0.8400 to 1.0000, up to 0.9400 to 1.0000. Every run still
clears the proposal criteria of precision 0.80 and recall 0.75.

Per-class recall on the four held-out stress runs:

| Anomaly type | Before | After |
|---|---|---|
| Speeding | 132 of 132, 1.00 | 132 of 132, 1.00 |
| Disengaged | 121 of 136, 0.89 | 121 of 136, 0.89 |
| Fabricated | 93 of 132, 0.70 | 132 of 132, 1.00 |

False positives on genuine interviews across the four stress runs rise from 6 to
30 out of 1,600, that is from 0.4 percent to 1.9 percent.

## Reading of the result

The diagnostic is confirmed. Fabricated recall on data the detector had never
seen moves from 0.70 to 1.00, which is what the entropy separation predicted
would happen if the estimator were corrected. The missed fabrications were a
calibration artefact and not a limit of univariate detection, and the held-out
evaluation establishes that independently of the development data on which the
argument was formed. Disengaged and speeding recall are unchanged, as expected,
since the change touches only the entropy rule.

The cost is real and it is not evenly distributed. Under the stress condition
the change is a clear improvement: recall rises by eight to thirteen points for
a precision cost of three to nine points. Under canonical difficulty it is pure
cost, because recall was already 1.00 there and the additional flags land only
on genuine interviews. The worst case is the five percent prevalence sweep,
where precision falls 12.8 points to 0.8333. That condition matters more than
its position in the table suggests, because real fabrication rates are usually
low, and at that prevalence the change adds four false accusations while
catching no additional anomaly.

The evaluation does not contain a low-prevalence stress run, which is the
condition that would resemble deployment most closely: subtle fabrication that
is also rare. Whether the recall gain would outweigh the precision cost there is
not answered by these datasets, and constructing that condition would require a
new evaluation rather than a re-reading of this one.

## Recommendation

Neither configuration is unambiguously better, and the choice is a judgement about
which error is more costly in the field. Missing a fabricated interview admits
false data into a dataset. Flagging a genuine one sends a real enumerator for
review on the strength of their timing. At the prevalences where fabrication
actually occurs, this change trades roughly four of the second for zero of the
first, and under stress conditions it trades a few of the second for many of the
first.

The evaluated system therefore leaves the fence off: it is frozen, documented,
reproducible and clears every committed criterion. The fence is shipped on `main`
as an option so that a deployment which judges a missed fabrication to be the
costlier error can turn it on with one configuration key, and this note is the
evidence that the limitation was diagnosed, that a principled correction exists,
and that its cost was measured rather than asserted.

Like every batch-relative threshold in the detector, the fence assumes that
anomalies are a minority of the batch. It is estimated from the median and upper
quartile of the batch it is applied to, so it does not address the loss of
detection at high prevalence reported in section 6.4 of the report.
