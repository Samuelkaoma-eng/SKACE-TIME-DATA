import pandas as pd
from io import StringIO
import numpy as np
import sys
import os

sys.path.append(os.path.abspath('.'))
from src.validation.anomaly_detector import AnomalyDetector

csv_data = """file_name,interview_id,V-01_total_interview_duration_ms,V-02_speed_trajectory_early,V-03_speed_trajectory_late,V-04_speed_trajectory_ratio,V-06_back_navigation_total_count,V-05_back_navigation_rate,V-07_time_of_day_hour,V-08_day_of_week,V-09_session_length_vs_median,V-10_zero_back_nav_flag,T-01_rt_variance,T-02_rt_iqr,T-03_rt_entropy,T-04_rt_skewness,T-05_rt_kurtosis,T-06_rt_mean,T-07_rt_median,T-08_rt_cv,T-09_rt_min,T-10_rt_max,S-01_mean_section_pace,S-02_section_duration_ms,S-03_within_section_variance,S-05_pause_count_5s,S-06_pause_count_30s,S-07_mean_pause_duration_ms,S-08_max_pause_duration_ms,S-09_back_nav_count_section,S-10_section_completion_rate,S-04_section_to_section_pace_ratio,Q-01_response_time_ms,Q-02_time_to_first_interaction,Q-03_edit_count,Q-04_revisit_flag,Q-05_revisit_count,Q-06_field_completion_ratio,Q-07_idle_time_ms,Q-08_keystroke_count,Q-09_constraint_trigger_count,Q-10_first_to_last_interaction_duration
surveycto.csv,INT500,0,0,0,,0,0.0,2,1,0.0,1,0,0,0.0,0.0,0.0,0,0,0.0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
surveycto.csv,INT501,-5000,2000,2000,1.0,2,0.1,10,3,-1.0,0,100,50,1.0,0.0,0.0,2000,2000,0.1,1500,2500,1800,-4000,1000,1,0,500,1000,0,1,1.0,2000,200,1,0,0,1.0,100,10,0,3000
surveycto.csv,INT502,15000,3000,0,,1,0.05,11,2,1.0,0,50000,200,1.2,0.1,-0.2,3000,2900,0.2,2000,3500,2000,10000,20000,2,0,1000,2000,0,1,1.0,3000,500,2,0,1,1.0,2000,20,0,12000
surveycto.csv,INT503,10000,2500,2600,1.04,0,0.0,13,5,1.2,1,10,5,0.1,0.0,0.0,2500,2500,0.01,2400,2600,2000,9000,10,0,0,0,0,0,1,1.0,2500,0,0,0,0,1.0,0,0,0,15000
surveycto.csv,INT504,20000,4000,4100,1.02,50,0.9,14,4,1.5,0,900000,1200,2.5,0.3,-0.4,4000,3900,0.3,2500,6000,3000,15000,500000,5,2,4000,9000,20,1,1.5,4000,800,15,1,10,0.85,5000,100,5,18000
surveycto.csv,INT505,12000,3000,3000,1.0,3,0.2,12,2,1.0,0,200000,800,2.0,0.2,-0.3,3000,2900,0.2,2000,4000,2500,11000,200000,2,1,2000,4000,1,1,1.0,3000,300,3,1,2,0.95,2000,30,1,11000
surveycto.csv,INT506,13000,3100,3200,1.03,4,0.3,12,2,1.1,0,210000,900,2.1,0.2,-0.2,3100,3000,0.21,2100,4200,2600,12000,210000,3,1,2200,4200,1,1,1.0,3100,400,4,1,2,0.96,2100,32,1,12000
odk.csv,ODK500,10000,2000,2100,1.05,0,0.0,9,1,1.0,1,5,2,0.05,0.0,0.0,2000,2000,0.01,1950,2050,1500,9000,5,0,0,0,0,0,1,1.0,2000,0,0,0,0,1.0,0,0,0,2000
odk.csv,ODK501,999999999,5000,5000,1.0,1,0.01,23,7,1000.0,0,9999999,5000,4.0,0.5,-0.1,5000,5000,0.9,1000,10000,5000,999999999,9999999,50,10,5000000,9000000,0,1,1.0,5000,2000,1,0,0,1.0,990000000,500,0,999999999
"""

df = pd.read_csv(StringIO(csv_data))
df = df.replace({'': np.nan, 'NULL': np.nan})

df['V-04_speed_trajectory_ratio'] = pd.to_numeric(df['V-04_speed_trajectory_ratio'], errors='coerce')

# Pipeline explicitly ensures mathematically undefined ratios are NaN
df.loc[df['V-02_speed_trajectory_early'] == 0, 'V-04_speed_trajectory_ratio'] = np.nan
df.loc[df['V-02_speed_trajectory_early'].isna(), 'V-04_speed_trajectory_ratio'] = np.nan

detector = AnomalyDetector()
results = detector.detect(df)

out_file = "output/final_combined_features_500series.csv"
results.to_csv(out_file, index=False, na_rep='NaN')
print(f"Validated and Saved {out_file}")

# Format clearly into console summary
print("\n[EVALUATION RESULTS]")
for idx, row in results.iterrows():
    c = row['anomaly_category']
    sc = row['anomaly_score']
    dq = row['is_data_quality_issue']
    print(f"{row['interview_id']} -> DQ: {dq} | Score: {sc} | Cat: {c}")
