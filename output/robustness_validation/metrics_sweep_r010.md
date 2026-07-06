# Metrics: sweep_r010

## Summary

```text
 total_samples  true_positive  true_negative  false_positive  false_negative  precision  recall  f1_score  accuracy  specificity  anomalies_true  anomalies_predicted  normals_true  normals_predicted  precision_threshold  recall_threshold  fabricated_score_threshold  normal_score_max  passes_precision_threshold  passes_recall_threshold  fabricated_total  fabricated_score_ge_threshold  normal_total  normal_score_le_threshold  passes_fabricated_score_threshold  passes_normal_score_threshold  passes_overall_contract
           500             50            450               0               0        1.0     1.0       1.0       1.0          1.0              50                   50           450                450                  0.8              0.75                           5                 1                        True                     True                16                             16           450                        450                               True                           True                     True
```

## Detection By Type

```text
anomaly_type  total  detected  detection_rate
  disengaged     18        18             1.0
  fabricated     16        16             1.0
    speeding     16        16             1.0
```
