# Metrics: sweep_r020

## Summary

```text
 total_samples  true_positive  true_negative  false_positive  false_negative  precision  recall  f1_score  accuracy  specificity  anomalies_true  anomalies_predicted  normals_true  normals_predicted  precision_threshold  recall_threshold  fabricated_score_threshold  normal_score_max  passes_precision_threshold  passes_recall_threshold  fabricated_total  fabricated_score_ge_threshold  normal_total  normal_score_le_threshold  passes_fabricated_score_threshold  passes_normal_score_threshold  passes_overall_contract
           500            100            398               2               0   0.980392     1.0  0.990099     0.996        0.995             100                  102           400                398                  0.8              0.75                           5                 1                        True                     True                33                             33           400                        398                               True                          False                    False
```

## Detection By Type

```text
anomaly_type  total  detected  detection_rate
  disengaged     34        34             1.0
  fabricated     33        33             1.0
    speeding     33        33             1.0
```
