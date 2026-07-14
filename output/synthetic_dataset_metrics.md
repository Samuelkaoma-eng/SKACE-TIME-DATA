# Synthetic Dataset Evaluation

## Metrics

```text
 total_samples  true_positive  true_negative  false_positive  false_negative  precision  recall  f1_score  accuracy  specificity  anomalies_true  anomalies_predicted  normals_true  normals_predicted  precision_threshold  recall_threshold  fabricated_score_threshold  normal_score_max  passes_precision_threshold  passes_recall_threshold  fabricated_total  fabricated_score_ge_threshold  normal_total  normal_score_le_threshold  passes_fabricated_score_threshold  passes_normal_score_threshold  passes_overall_contract dataset    format  runtime_seconds                                             source_file
         10000           2000           7989              11               0   0.994530     1.0  0.997258    0.9989     0.998625            2000                 2011          8000               7989                  0.8              0.75                           5                 1                        True                     True               666                            666          8000                       7989                               True                          False                    False  n10000 surveycto          1037.74 data\synthetic_datasets\n10000\audit_logs_surveycto.csv
          2000            400           1599               1               0   0.997506     1.0  0.998752    0.9995     0.999375             400                  401          1600               1599                  0.8              0.75                           5                 1                        True                     True               133                            133          1600                       1599                               True                          False                    False   n2000 surveycto           222.88  data\synthetic_datasets\n2000\audit_logs_surveycto.csv
           500            100            400               0               0   1.000000     1.0  1.000000    1.0000     1.000000             100                  100           400                400                  0.8              0.75                           5                 1                        True                     True                33                             33           400                        400                               True                           True                     True    n500       odk            46.38         data\synthetic_datasets\n500\audit_logs_odk.csv
           500            100            400               0               0   1.000000     1.0  1.000000    1.0000     1.000000             100                  100           400                400                  0.8              0.75                           5                 1                        True                     True                33                             33           400                        400                               True                           True                     True    n500 surveycto            57.54   data\synthetic_datasets\n500\audit_logs_surveycto.csv
```

## Detection By Type

```text
anomaly_type  total  detected  detection_rate dataset    format
  disengaged    668       668             1.0  n10000 surveycto
  fabricated    666       666             1.0  n10000 surveycto
    speeding    666       666             1.0  n10000 surveycto
  disengaged    134       134             1.0   n2000 surveycto
  fabricated    133       133             1.0   n2000 surveycto
    speeding    133       133             1.0   n2000 surveycto
  disengaged     34        34             1.0    n500       odk
  fabricated     33        33             1.0    n500       odk
    speeding     33        33             1.0    n500       odk
  disengaged     34        34             1.0    n500 surveycto
  fabricated     33        33             1.0    n500 surveycto
    speeding     33        33             1.0    n500 surveycto
```
