# Strict Examiner Audit Report

## Checklist Results

```text
                                                step  passed                                                                                                                                                                                                                                                                                                                                              details
                     surveycto: raw required columns    True                                                                                                                                                                                                                                                           Required columns present: ['interview_id', 'node', 'event', 'start', 'end', 'duration_ms']
                         surveycto: timestamp format    True                                                                                                                                                                                                                                                                               Sample timestamps: ['1672646400000', '1672646406500', '1672646406900']
                               surveycto: CIR schema    True                                                                                                                                                                                                                                                       CIR columns: ['interview_id', 'field_name', 'event_type', 'start_ms', 'end_ms', 'duration_ms']
                 surveycto: CIR duration consistency    True                                                                                                                                                                                                                                                                                     interview_id=INT-00001 field=demographics_q01 duration_ms=6000.0
              surveycto: manual Q-01 aggregate check    True                                                                                                                                                                                                                                                                                     interview=INT-00001 field_count=20 chosen_field=demographics_q01
                        surveycto: manual V-01 check    True                                                                                                                                                                                                                                                                                                                      manual=133500.0 pipeline=133500
                        surveycto: manual T-02 check    True                                                                                                                                                                                                                                                                                                                              manual=0.0 pipeline=0.0
             surveycto: anomaly score reconstruction    True                                                                                                                                                                                                                                                                                                                                  expected=7 actual=7
                           surveycto: status mapping    True                                                                                                                                                                                                                                                                                                                      expected=FLAGGED actual=FLAGGED
surveycto: fabricated vs normal signature separation    True anomaly_type  count  mean_rt_variance  mean_rt_iqr  mean_rt_entropy  mean_back_nav_count  mean_total_duration_ms\n      normal    400      2.332537e+07  5040.055625         3.245894                 2.08             187789.3675\n  fabricated     33      0.000000e+00     0.000000         0.000000                 0.00               3790.0000
                           odk: raw required columns    True                                                                                                                                                                                                                                                                 Required columns present: ['instance_id', 'name', 'event', 'start_time', 'end_time']
                               odk: timestamp format    True                                                                                                                                                                                                                               Sample timestamps: ['2023-01-02T08:00:00.000+00:00', '2023-01-02T08:00:06.500+00:00', '2023-01-02T08:00:06.900+00:00']
                                     odk: CIR schema    True                                                                                                                                                                                                                                                       CIR columns: ['interview_id', 'field_name', 'event_type', 'start_ms', 'end_ms', 'duration_ms']
                       odk: CIR duration consistency    True                                                                                                                                                                                                                                                                                     interview_id=INT-00001 field=demographics_q01 duration_ms=6000.0
                                 cross-format parity    True                                                                                                                                                                                                                                                                         surveycto precision/recall=0.9901/1.0000, odk precision/recall=0.9901/1.0000
          scale stability (n500 vs n10000 surveycto)    True                                                                                                                                                                                                                                                      runtime_ratio=19.86, n500 precision/recall=0.9901/1.0000, n10000 precision/recall=0.9857/1.0000
```

## Metrics Summary

```text
{
  "datasets": {
    "surveycto": {
      "metrics": {
        "total_samples": 500,
        "true_positive": 100,
        "true_negative": 399,
        "false_positive": 1,
        "false_negative": 0,
        "precision": 0.9900990099009901,
        "recall": 1.0,
        "f1_score": 0.9950248756218906,
        "accuracy": 0.998,
        "specificity": 0.9975,
        "anomalies_true": 100,
        "anomalies_predicted": 101,
        "normals_true": 400,
        "normals_predicted": 399,
        "precision_threshold": 0.8,
        "recall_threshold": 0.75,
        "fabricated_score_threshold": 5,
        "normal_score_max": 1,
        "passes_precision_threshold": true,
        "passes_recall_threshold": true,
        "fabricated_total": 33,
        "fabricated_score_ge_threshold": 33,
        "normal_total": 400,
        "normal_score_le_threshold": 399,
        "passes_fabricated_score_threshold": true,
        "passes_normal_score_threshold": false,
        "passes_overall_contract": false
      },
      "runtime_seconds": 32.76,
      "baseline_duration_iqr": {
        "total_samples": 500,
        "true_positive": 66,
        "true_negative": 400,
        "false_positive": 0,
        "false_negative": 34,
        "precision": 1.0,
        "recall": 0.66,
        "f1_score": 0.7951807228915663,
        "accuracy": 0.932,
        "specificity": 1.0,
        "anomalies_true": 100,
        "anomalies_predicted": 66,
        "normals_true": 400,
        "normals_predicted": 434,
        "precision_threshold": 0.8,
        "recall_threshold": 0.75,
        "fabricated_score_threshold": 5,
        "normal_score_max": 1,
        "passes_precision_threshold": true,
        "passes_recall_threshold": false,
        "fabricated_total": 0,
        "fabricated_score_ge_threshold": 0,
        "normal_total": 400,
        "normal_score_le_threshold": 0,
        "passes_fabricated_score_threshold": false,
        "passes_normal_score_threshold": false,
        "passes_overall_contract": false
      },
      "baseline_zero_back_nav": {
        "total_samples": 500,
        "true_positive": 66,
        "true_negative": 345,
        "false_positive": 55,
        "false_negative": 34,
        "precision": 0.5454545454545454,
        "recall": 0.66,
        "f1_score": 0.5972850678733032,
        "accuracy": 0.822,
        "specificity": 0.8625,
        "anomalies_true": 100,
        "anomalies_predicted": 121,
        "normals_true": 400,
        "normals_predicted": 379,
        "precision_threshold": 0.8,
        "recall_threshold": 0.75,
        "fabricated_score_threshold": 5,
        "normal_score_max": 1,
        "passes_precision_threshold": false,
        "passes_recall_threshold": false,
        "fabricated_total": 0,
        "fabricated_score_ge_threshold": 0,
        "normal_total": 400,
        "normal_score_le_threshold": 0,
        "passes_fabricated_score_threshold": false,
        "passes_normal_score_threshold": false,
        "passes_overall_contract": false
      }
    },
    "odk": {
      "metrics": {
        "total_samples": 500,
        "true_positive": 100,
        "true_negative": 399,
        "false_positive": 1,
        "false_negative": 0,
        "precision": 0.9900990099009901,
        "recall": 1.0,
        "f1_score": 0.9950248756218906,
        "accuracy": 0.998,
        "specificity": 0.9975,
        "anomalies_true": 100,
        "anomalies_predicted": 101,
        "normals_true": 400,
        "normals_predicted": 399,
        "precision_threshold": 0.8,
        "recall_threshold": 0.75,
        "fabricated_score_threshold": 5,
        "normal_score_max": 1,
        "passes_precision_threshold": true,
        "passes_recall_threshold": true,
        "fabricated_total": 33,
        "fabricated_score_ge_threshold": 33,
        "normal_total": 400,
        "normal_score_le_threshold": 399,
        "passes_fabricated_score_threshold": true,
        "passes_normal_score_threshold": false,
        "passes_overall_contract": false
      },
      "runtime_seconds": 30.95
    }
  },
  "scale": {
    "n500_runtime_seconds": 33.04,
    "n10000_runtime_seconds": 656.33,
    "runtime_ratio": 19.864709443099276,
    "n500_metrics": {
      "total_samples": 500,
      "true_positive": 100,
      "true_negative": 399,
      "false_positive": 1,
      "false_negative": 0,
      "precision": 0.9900990099009901,
      "recall": 1.0,
      "f1_score": 0.9950248756218906,
      "accuracy": 0.998,
      "specificity": 0.9975,
      "anomalies_true": 100,
      "anomalies_predicted": 101,
      "normals_true": 400,
      "normals_predicted": 399,
      "precision_threshold": 0.8,
      "recall_threshold": 0.75,
      "fabricated_score_threshold": 5,
      "normal_score_max": 1,
      "passes_precision_threshold": true,
      "passes_recall_threshold": true,
      "fabricated_total": 33,
      "fabricated_score_ge_threshold": 33,
      "normal_total": 400,
      "normal_score_le_threshold": 399,
      "passes_fabricated_score_threshold": true,
      "passes_normal_score_threshold": false,
      "passes_overall_contract": false
    },
    "n10000_metrics": {
      "total_samples": 10000,
      "true_positive": 2000,
      "true_negative": 7971,
      "false_positive": 29,
      "false_negative": 0,
      "precision": 0.9857072449482503,
      "recall": 1.0,
      "f1_score": 0.9928021841648051,
      "accuracy": 0.9971,
      "specificity": 0.996375,
      "anomalies_true": 2000,
      "anomalies_predicted": 2029,
      "normals_true": 8000,
      "normals_predicted": 7971,
      "precision_threshold": 0.8,
      "recall_threshold": 0.75,
      "fabricated_score_threshold": 5,
      "normal_score_max": 1,
      "passes_precision_threshold": true,
      "passes_recall_threshold": true,
      "fabricated_total": 666,
      "fabricated_score_ge_threshold": 666,
      "normal_total": 8000,
      "normal_score_le_threshold": 7971,
      "passes_fabricated_score_threshold": true,
      "passes_normal_score_threshold": false,
      "passes_overall_contract": false
    }
  }
}
```
