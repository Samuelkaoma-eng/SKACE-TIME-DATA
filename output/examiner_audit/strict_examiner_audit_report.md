# Strict Examiner Audit Report

## Checklist Results

```text
                                                step  passed                                                                                                                                                                                                                                                                                                                                              details
                     surveycto: raw required columns    True                                                                                                                                                                                                                                                           Required columns present: ['interview_id', 'node', 'event', 'start', 'end', 'duration_ms']
                         surveycto: timestamp format    True                                                                                                                                                                                                                                                                               Sample timestamps: ['1672646400000', '1672646401312', '1672646408353']
                               surveycto: CIR schema    True                                                                                                                                                                                                                                                       CIR columns: ['interview_id', 'field_name', 'event_type', 'start_ms', 'end_ms', 'duration_ms']
                 surveycto: CIR duration consistency    True                                                                                                                                                                                                                                                                                        interview_id=INT-00001 field=unknown_field duration_ms=1020.0
              surveycto: manual Q-01 aggregate check    True                                                                                                                                                                                                                                                                                     interview=INT-00001 field_count=20 chosen_field=demographics_q01
                        surveycto: manual V-01 check    True                                                                                                                                                                                                                                                                                                                      manual=141418.0 pipeline=141418
                        surveycto: manual T-02 check    True                                                                                                                                                                                                                                                                                                                        manual=215.75 pipeline=215.75
             surveycto: anomaly score reconstruction    True                                                                                                                                                                                                                                                                                                                                  expected=6 actual=6
                           surveycto: status mapping    True                                                                                                                                                                                                                                                                                                                      expected=FLAGGED actual=FLAGGED
surveycto: fabricated vs normal signature separation    True anomaly_type  count  mean_rt_variance  mean_rt_iqr  mean_rt_entropy  mean_back_nav_count  mean_total_duration_ms\n      normal    400      2.658835e+07  5567.766250         3.299218               1.9275           184106.052500\n  fabricated     33      6.744830e+03   103.909091         0.052072               0.0000            28762.090909
                           odk: raw required columns    True                                                                                                                                                                                                                                                                 Required columns present: ['instance_id', 'name', 'event', 'start_time', 'end_time']
                               odk: timestamp format    True                                                                                                                                                                                                                               Sample timestamps: ['2023-01-02T08:00:00.000+00:00', '2023-01-02T08:00:02.569+00:00', '2023-01-02T08:00:09.831+00:00']
                                     odk: CIR schema    True                                                                                                                                                                                                                                                       CIR columns: ['interview_id', 'field_name', 'event_type', 'start_ms', 'end_ms', 'duration_ms']
                       odk: CIR duration consistency    True                                                                                                                                                                                                                                                                                        interview_id=INT-00001 field=unknown_field duration_ms=2449.0
                                 cross-format parity    True                                                                                                                                                                                                                                                                         surveycto precision/recall=1.0000/1.0000, odk precision/recall=1.0000/1.0000
          scale stability (n500 vs n10000 surveycto)    True                                                                                                                                                                                                                                                      runtime_ratio=19.05, n500 precision/recall=1.0000/1.0000, n10000 precision/recall=0.9945/1.0000
```

## Metrics Summary

```text
{
  "datasets": {
    "surveycto": {
      "metrics": {
        "total_samples": 500,
        "true_positive": 100,
        "true_negative": 400,
        "false_positive": 0,
        "false_negative": 0,
        "precision": 1.0,
        "recall": 1.0,
        "f1_score": 1.0,
        "accuracy": 1.0,
        "specificity": 1.0,
        "anomalies_true": 100,
        "anomalies_predicted": 100,
        "normals_true": 400,
        "normals_predicted": 400,
        "precision_threshold": 0.8,
        "recall_threshold": 0.75,
        "fabricated_score_threshold": 5,
        "normal_score_max": 1,
        "passes_precision_threshold": true,
        "passes_recall_threshold": true,
        "fabricated_total": 33,
        "fabricated_score_ge_threshold": 33,
        "normal_total": 400,
        "normal_score_le_threshold": 400,
        "passes_fabricated_score_threshold": true,
        "passes_normal_score_threshold": true,
        "passes_overall_contract": true
      },
      "runtime_seconds": 50.17,
      "baseline_duration_iqr": {
        "total_samples": 500,
        "true_positive": 66,
        "true_negative": 397,
        "false_positive": 3,
        "false_negative": 34,
        "precision": 0.9565217391304348,
        "recall": 0.66,
        "f1_score": 0.7810650887573964,
        "accuracy": 0.926,
        "specificity": 0.9925,
        "anomalies_true": 100,
        "anomalies_predicted": 69,
        "normals_true": 400,
        "normals_predicted": 431,
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
        "true_negative": 324,
        "false_positive": 76,
        "false_negative": 34,
        "precision": 0.4647887323943662,
        "recall": 0.66,
        "f1_score": 0.5454545454545454,
        "accuracy": 0.78,
        "specificity": 0.81,
        "anomalies_true": 100,
        "anomalies_predicted": 142,
        "normals_true": 400,
        "normals_predicted": 358,
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
        "true_negative": 400,
        "false_positive": 0,
        "false_negative": 0,
        "precision": 1.0,
        "recall": 1.0,
        "f1_score": 1.0,
        "accuracy": 1.0,
        "specificity": 1.0,
        "anomalies_true": 100,
        "anomalies_predicted": 100,
        "normals_true": 400,
        "normals_predicted": 400,
        "precision_threshold": 0.8,
        "recall_threshold": 0.75,
        "fabricated_score_threshold": 5,
        "normal_score_max": 1,
        "passes_precision_threshold": true,
        "passes_recall_threshold": true,
        "fabricated_total": 33,
        "fabricated_score_ge_threshold": 33,
        "normal_total": 400,
        "normal_score_le_threshold": 400,
        "passes_fabricated_score_threshold": true,
        "passes_normal_score_threshold": true,
        "passes_overall_contract": true
      },
      "runtime_seconds": 57.46
    }
  },
  "scale": {
    "n500_runtime_seconds": 56.12,
    "n10000_runtime_seconds": 1068.87,
    "runtime_ratio": 19.04615110477548,
    "n500_metrics": {
      "total_samples": 500,
      "true_positive": 100,
      "true_negative": 400,
      "false_positive": 0,
      "false_negative": 0,
      "precision": 1.0,
      "recall": 1.0,
      "f1_score": 1.0,
      "accuracy": 1.0,
      "specificity": 1.0,
      "anomalies_true": 100,
      "anomalies_predicted": 100,
      "normals_true": 400,
      "normals_predicted": 400,
      "precision_threshold": 0.8,
      "recall_threshold": 0.75,
      "fabricated_score_threshold": 5,
      "normal_score_max": 1,
      "passes_precision_threshold": true,
      "passes_recall_threshold": true,
      "fabricated_total": 33,
      "fabricated_score_ge_threshold": 33,
      "normal_total": 400,
      "normal_score_le_threshold": 400,
      "passes_fabricated_score_threshold": true,
      "passes_normal_score_threshold": true,
      "passes_overall_contract": true
    },
    "n10000_metrics": {
      "total_samples": 10000,
      "true_positive": 2000,
      "true_negative": 7989,
      "false_positive": 11,
      "false_negative": 0,
      "precision": 0.9945300845350572,
      "recall": 1.0,
      "f1_score": 0.9972575417601596,
      "accuracy": 0.9989,
      "specificity": 0.998625,
      "anomalies_true": 2000,
      "anomalies_predicted": 2011,
      "normals_true": 8000,
      "normals_predicted": 7989,
      "precision_threshold": 0.8,
      "recall_threshold": 0.75,
      "fabricated_score_threshold": 5,
      "normal_score_max": 1,
      "passes_precision_threshold": true,
      "passes_recall_threshold": true,
      "fabricated_total": 666,
      "fabricated_score_ge_threshold": 666,
      "normal_total": 8000,
      "normal_score_le_threshold": 7989,
      "passes_fabricated_score_threshold": true,
      "passes_normal_score_threshold": false,
      "passes_overall_contract": false
    }
  }
}
```
