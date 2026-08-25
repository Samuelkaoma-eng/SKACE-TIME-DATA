# Change: distribution-relative entropy fence

Branch `fix/entropy-threshold-relative`. This is the rule adjustment arising from
`docs/fabricated_detection_diagnostic.md`, prepared under the frozen-evaluation
discipline agreed for it.

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
uncontaminated side of the distribution:

    fence = median - entropy_fence_scale * (Q3 - median)

with `entropy_fence_scale` defaulting to 3.0 and a minimum sample of 30 before
the fence is applied at all.

## Why this form and not another

Every anomaly profile in scope depresses entropy and none raises it, so the upper
half of the entropy distribution contains no anomalies by construction. Estimating
the scale from that half alone therefore removes the contamination that made the
plain fence ineffective. This is the masking problem in unsupervised outlier
detection, where the estimator is computed from a sample that includes the
outliers it is meant to isolate.

For a symmetric distribution `Q3 - median` is half the interquartile range, so
`median - 3 * (Q3 - median)` reduces exactly to Tukey's `Q1 - 1.5 * IQR`. The
change is therefore not a new or weaker fence. It is the same fence, estimated in
a way the anomalies cannot move.

The choice follows the precedent already set in this project. The earlier
de-tuning round removed a fixed 280,000 ms pause constant in favour of a rule
relative to each dataset's own median, and `low_rt_iqr_median_ratio` and
`low_mean_rt_median_ratio` are both already relative. The entropy constant was
the last hard-coded behavioural threshold remaining.

No threshold was selected by comparing candidate values against results. The form
was derived from the contamination argument above, and the scale factor of 3.0 is
the value that makes it equivalent to the existing Tukey fence.

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

Not yet run at the time this file was committed.
