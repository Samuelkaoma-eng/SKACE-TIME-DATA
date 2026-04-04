# Synthetic Dataset Evaluation

## Metrics

```text
 total_samples  true_positive  true_negative  false_positive  false_negative  precision  recall  f1_score  accuracy  specificity  anomalies_true  anomalies_predicted  normals_true  normals_predicted dataset    format  runtime_seconds                                             source_file  precision_threshold  recall_threshold  fabricated_score_threshold  normal_score_max passes_precision_threshold passes_recall_threshold  fabricated_total  fabricated_score_ge_threshold  normal_total  normal_score_le_threshold passes_fabricated_score_threshold passes_normal_score_threshold passes_overall_contract
         10000           1999           7940              60               1    0.97086  0.9995  0.984972    0.9939       0.9925            2000                 2059          8000               7941  n10000 surveycto           705.03 data\synthetic_datasets\n10000\audit_logs_surveycto.csv                  NaN               NaN                         NaN               NaN                        NaN                     NaN               NaN                            NaN           NaN                        NaN                               NaN                           NaN                     NaN
          2000            400           1600               0               0    1.00000  1.0000  1.000000    1.0000       1.0000             400                  400          1600               1600   n2000 surveycto           203.52  data\synthetic_datasets\n2000\audit_logs_surveycto.csv                  0.8              0.75                         5.0               1.0                       True                    True             133.0                          133.0        1600.0                     1600.0                              True                          True                    True
           500            100            400               0               0    1.00000  1.0000  1.000000    1.0000       1.0000             100                  100           400                400    n500       odk            41.23         data\synthetic_datasets\n500\audit_logs_odk.csv                  0.8              0.75                         5.0               1.0                       True                    True              33.0                           33.0         400.0                      400.0                              True                          True                    True
           500            100            400               0               0    1.00000  1.0000  1.000000    1.0000       1.0000             100                  100           400                400    n500 surveycto            57.59   data\synthetic_datasets\n500\audit_logs_surveycto.csv                  0.8              0.75                         5.0               1.0                       True                    True              33.0                           33.0         400.0                      400.0                              True                          True                    True
```

## Detection By Type

```text
dataset    format anomaly_type  total  detected  detection_rate
 n10000 surveycto   disengaged    668       667        0.998503
 n10000 surveycto   fabricated    666       666        1.000000
 n10000 surveycto     speeding    666       666        1.000000
  n2000 surveycto   disengaged    134       134        1.000000
  n2000 surveycto   fabricated    133       133        1.000000
  n2000 surveycto     speeding    133       133        1.000000
   n500       odk   disengaged     34        34        1.000000
   n500       odk   fabricated     33        33        1.000000
   n500       odk     speeding     33        33        1.000000
   n500 surveycto   disengaged     34        34        1.000000
   n500 surveycto   fabricated     33        33        1.000000
   n500 surveycto     speeding     33        33        1.000000
```
