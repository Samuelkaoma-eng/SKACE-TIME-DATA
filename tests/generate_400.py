import pandas as pd
from io import StringIO
import numpy as np
import sys
import os

# Fix path to import src
sys.path.append(os.path.abspath('.'))
from src.validation.anomaly_detector import AnomalyDetector

csv_data = """file_name,interview_id,V-01_total_interview_duration_ms,V-02_speed_trajectory_early,V-03_speed_trajectory_late,V-04_speed_trajectory_ratio,V-06_back_navigation_total_count,V-05_back_navigation_rate,V-07_time_of_day_hour,V-08_day_of_week,V-09_session_length_vs_median,V-10_zero_back_nav_flag,T-01_rt_variance,T-02_rt_iqr,T-03_rt_entropy,T-04_rt_skewness,T-05_rt_kurtosis,T-06_rt_mean,T-07_rt_median,T-08_rt_cv,T-09_rt_min,T-10_rt_max,S-01_mean_section_pace,S-02_section_duration_ms,S-03_within_section_variance,S-05_pause_count_5s,S-06_pause_count_30s,S-07_mean_pause_duration_ms,S-08_max_pause_duration_ms,S-09_back_nav_count_section,S-10_section_completion_rate,S-04_section_to_section_pace_ratio,Q-01_response_time_ms,Q-02_time_to_first_interaction,Q-03_edit_count,Q-04_revisit_flag,Q-05_revisit_count,Q-06_field_completion_ratio,Q-07_idle_time_ms,Q-08_keystroke_count,Q-09_constraint_trigger_count,Q-10_first_to_last_interaction_duration,anomaly_score,flag_iqr_duration,flag_rule_min_dur,flag_rule_zero_back,flag_rule_low_entropy,flag_rule_uniform_timing,flag_rule_pause,is_data_quality_issue,is_anomalous_behavior,is_anomalous
surveycto.csv,INT400,18000,4200,4800,1.14,3,0.15,9,2,1.1,0,850000,900,2.1,0.2,-0.5,4200,4100,0.21,2800,5500,3000,9000,400000,3,0,2000,4000,1,1,1.0,4200,500,3,1,2,0.95,2000,35,1,8000,0,0,0,0,0,0,0,0,0,0
surveycto.csv,INT401,3500,0,1200,0,0,0,11,3,0.4,1,0,0,0,0,0,900,900,0,900,900,500,2000,0,0,0,0,0,0,1,0.5,900,0,0,0,0,1.0,0,5,0,900,3,0,1,1,1,1,0,0,1,1
surveycto.csv,INT402,7200000,2000,2100,1.05,1,0.02,14,4,50,0,10000,200,1.8,0.1,-0.2,2000,2100,0.1,1500,2600,1800,7000000,10000,10,3,300000,1000000,0,1,1.0,2000,1000,1,0,0,1.0,6800000,20,0,7100000,4,1,0,0,0,0,1,0,1,1
surveycto.csv,INT403,8000,0,0,0,0,0,10,2,0.7,1,0,0,0,0,0,4000,4000,0,4000,4000,2000,4000,0,0,0,0,0,0,1,0.5,4000,0,0,0,0,1.0,0,0,0,4000,5,0,0,1,1,1,0,0,1,1
surveycto.csv,INT404,25000,3000,3200,1.06,15,0.6,16,5,1.5,0,900000,1100,2.3,0.4,-0.6,3500,3400,0.3,2000,6000,2800,12000,450000,6,2,4000,9000,5,1,1.2,3500,600,10,1,6,0.9,5000,60,2,20000,3,0,0,0,0,0,1,0,1,1
surveycto.csv,INT405,14000,3800,3900,1.02,2,0.1,13,2,0.9,0,300000,600,1.7,0.1,-0.3,3800,3700,0.15,2500,5000,2600,7000,200000,2,0,1500,3000,1,1,1.0,3800,300,2,0,1,1.0,1000,30,0,12000,1,0,0,0,0,0,0,0,0,0
surveycto.csv,INT406,6000,2500,2600,1.04,1,0.1,15,1,0.6,0,20000,200,1.5,0.0,0.0,2600,2550,0.08,2000,3000,2000,5000,15000,1,0,1000,2000,0,1,1.0,2600,200,1,0,0,1.0,500,20,0,5000,2,0,0,0,0,0,0,0,1,1
surveycto.csv,INT407,20000,4200,4300,1.02,0,0,12,6,1.3,1,5000,100,0.5,0.0,0.0,4200,4200,0.02,4000,4400,2100,10000,5000,0,0,0,0,0,1,1.0,4200,0,0,0,0,1.0,0,0,0,4200,4,0,0,1,1,1,0,0,1,1
odk.csv,ODK400,17000,4000,4500,1.12,4,0.2,8,2,1.0,0,800000,900,2.0,0.2,-0.4,4000,3900,0.2,2700,5200,2900,8000,300000,2,0,1800,3500,1,1,1.0,4000,400,2,1,2,0.95,1500,30,1,7500,0,0,0,0,0,0,0,0,0,0
odk.csv,ODK401,4000,0,1000,0,0,0,11,3,0.5,1,0,0,0,0,0,1000,1000,0,1000,1000,500,2000,0,0,0,0,0,0,1,0.5,1000,0,0,0,0,1.0,0,5,0,1000,3,0,1,1,1,1,0,0,1,1
odk.csv,ODK402,3600000,1800,1900,1.05,2,0.05,14,4,30,0,12000,300,1.9,0.1,-0.2,1800,1850,0.1,1400,2200,1700,3500000,8000,8,2,200000,800000,0,1,1.0,1800,800,1,0,0,1.0,3400000,15,0,3500000,4,1,0,0,0,0,1,0,1,1
odk.csv,ODK403,9000,0,0,0,0,0,10,2,0.8,1,0,0,0,0,0,4500,4500,0,4500,4500,2200,5000,0,0,0,0,0,0,1,0.5,4500,0,0,0,0,1.0,0,0,0,4500,5,0,0,1,1,1,0,0,1,1
odk.csv,ODK404,22000,3000,3100,1.03,12,0.5,17,5,1.4,0,850000,1000,2.2,0.3,-0.5,3400,3300,0.28,2100,5800,2700,11000,420000,5,2,3500,8000,4,1,1.1,3400,500,8,1,5,0.92,4000,55,2,18000,3,0,0,0,0,0,1,0,1,1
odk.csv,ODK405,12000,3500,3600,1.02,2,0.1,13,2,0.9,0,250000,500,1.6,0.1,-0.3,3600,3500,0.14,2400,4800,2500,6000,180000,2,0,1400,2800,1,1,1.0,3600,300,2,0,1,1.0,900,25,0,11000,1,0,0,0,0,0,0,0,0,0
odk.csv,ODK406,5000,2500,2600,1.04,1,0.1,15,1,0.6,0,15000,200,1.4,0.0,0.0,2600,2550,0.08,2000,3000,2000,5000,10000,1,0,1000,2000,0,1,1.0,2600,200,1,0,0,1.0,500,20,0,5000,2,0,0,0,0,0,0,0,1,1
odk.csv,ODK407,20000,4200,4300,1.02,0,0,12,6,1.3,1,4000,100,0.4,0.0,0.0,4200,4200,0.02,4000,4400,2100,10000,4000,0,0,0,0,0,1,1.0,4200,0,0,0,0,1.0,0,0,0,4200,4,0,0,1,1,1,0,0,1,1
surveycto.csv,INT408,10000,1000,1000,,,0.1,10,2,1.0,0,1000,100,,0.1,0.0,2000,2000,0.1,1000,3000,2000,10000,5000,1,0,1000,2000,0,1,1.0,,,,,1.0,1000,10,0,8000,0,0,0,0,0,0,0,0,0,0
surveycto.csv,INT409,50000,2000,2000,1.0,15,0.7,12,3,2.0,0,8000000,2500,5.5,0.2,-0.1,3000,2800,0.5,1000,8000,3000,50000,100000,0,0,0,0,0,1,1.0,3000,500,0,1,0,1.0,40000,2,0,45000,0,0,0,0,0,0,0,0,0,0
"""
df = pd.read_csv(StringIO(csv_data))
df = df.replace({'': np.nan, 'NULL': np.nan})
df['V-04_speed_trajectory_ratio'] = pd.to_numeric(df['V-04_speed_trajectory_ratio'], errors='coerce')

# Fix ratio consistency mathematically (v-02 == 0 -> v-04 = nan)
df.loc[df['V-02_speed_trajectory_early'] == 0, 'V-04_speed_trajectory_ratio'] = np.nan

# Drop the old dummy flag columns
cols_to_drop = [c for c in df.columns if c.startswith('flag_') or c.startswith('is_') or c == 'anomaly_score']
df = df.drop(columns=cols_to_drop)

# Process
detector = AnomalyDetector()
results = detector.detect(df)

# Output
results.to_csv('output/final_combined_features_400series.csv', index=False)
print("Saved evaluated 400-series features to `output/final_combined_features_400series.csv`")
