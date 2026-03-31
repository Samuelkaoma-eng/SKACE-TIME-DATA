# SKACE-Time-Data: Validation Report

This report serves as the formal academic deliverable proving the detection precision of the
`AnomalyDetector` engine against the structured `400-Series` Ground Truth Dataset.
Aligned with thesis evaluation methodology (§5).

## 1. Classification Metrics (Binary Detection)

Threshold: `Normal` vs `Suspicious / Anomalous / DQ_Issue`

| Metric    | System  | Baseline 1 (Duration IQR) | Baseline 2 (Zero Back-Nav) |
|-----------|---------|---------------------------|---------------------------|
| Precision | 1.0000 | 0.0000             | 0.9333              |
| Recall    | 0.7778    | 0.0000              | 0.7778               |
| F1-Score  | 0.8750        | 0.0000               | 0.8485                |

**Success threshold (thesis §5)**: Precision >= 0.80, Recall >= 0.75 -> PASS

Categorical Alignment (exact bin match): 58.33%
Matched interviews: 24 of 24 ground-truth records
Confusion matrix: TP=14, FP=0, FN=4, TN=6

## 2. Effect Size Analysis (Cohen's d)

Separation between normal and anomalous anomaly_score distributions:

*   **Cohen's d**: 2.03

*(d > 0.8 = large effect size per Cohen [1988]. Demonstrates the scoring formula
unequivocally separates valid sessions from compromised records.)*

## 3. Per-Feature Discriminability (Mann-Whitney U Tests)

Thesis §5 requires Mann-Whitney U comparison per feature with Cohen's d effect sizes.
Features not meeting p < 0.05 and |d| >= 0.5 are documented for potential exclusion.

  Feature                                        p-value   Cohen d  Discriminative
  ---------------------------------------------------------------------------
  T-03_rt_entropy                                 0.0000   -10.746  YES
  T-02_rt_iqr                                     0.0001    -6.359  YES
  T-01_rt_variance                                0.0001    -2.263  YES
  V-01_total_interview_duration_ms                0.0003    -2.957  YES
  V-09_session_length_vs_median                   0.0003    -2.957  YES
  T-06_rt_mean                                    0.0003    -2.954  YES
  S-03_within_section_variance                    0.0003    -2.259  YES
  T-10_rt_max                                     0.0003    -3.752  YES
  S-01_mean_section_pace                          0.0003    -2.953  YES
  S-02_section_duration_ms                        0.0003    -2.957  YES
  Q-01_response_time_ms                           0.0003    -2.953  YES
  Q-02_time_to_first_interaction                  0.0003    -3.158  YES
  Q-10_first_to_last_interaction_duration         0.0003    -2.953  YES
  T-08_rt_cv                                      0.0004    -2.911  YES
  T-07_rt_median                                  0.0007    -2.564  YES
  S-08_max_pause_duration_ms                      0.0019    -1.940  YES
  V-03_speed_trajectory_late                      0.0031    -2.464  YES
  S-07_mean_pause_duration_ms                     0.0048    -1.545  YES
  T-04_rt_skewness                                0.0066    -1.823  YES
  V-02_speed_trajectory_early                     0.0095    -1.985  YES
  Q-06_field_completion_ratio                     0.0266    -1.221  YES
  T-09_rt_min                                     0.0464    -0.798  YES
  V-04_speed_trajectory_ratio                     0.0510    -0.538  NO
  V-05_back_navigation_rate                       0.0834    -0.098  NO
  Q-03_edit_count                                 0.0834     0.058  NO
  Q-04_revisit_flag                               0.0834     0.058  NO
  Q-08_keystroke_count                            0.0834     0.058  NO
  Q-05_revisit_count                              0.0834     0.058  NO
  V-06_back_navigation_total_count                0.0834     0.058  NO
  S-04_section_to_section_pace_ratio              0.1201    -0.782  NO
  V-07_time_of_day_hour                           0.1507     0.712  NO
  Q-07_idle_time_ms                               0.2179     0.202  NO
  T-05_rt_kurtosis                                0.6950    -0.830  NO
  S-09_back_nav_count_section                     1.0000     0.000  NO
  S-10_section_completion_rate                    1.0000     0.000  NO
  S-05_pause_count_5s                             1.0000     0.000  NO
  V-08_day_of_week                                1.0000     0.000  NO
  V-10_zero_back_nav_flag                         1.0000     0.000  NO
  S-06_pause_count_30s                            1.0000     0.000  NO
  Q-09_constraint_trigger_count                   1.0000     0.000  NO

  Discriminative features (p<0.05, |d|>=0.5): 22/40

## 4. Ground Truth Data

Baseline dataset: `24` explicitly engineered signatures across 4 anomaly
profiles (normal, fabricated, speeding, disengaged/dq_issue) in SurveyCTO and ODK formats.
Ground truth labels saved to: `data/ground_truth_labels.csv`
