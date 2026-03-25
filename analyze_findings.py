import sys
import traceback
try:
    import pandas as pd
    import glob, os

    files = glob.glob('output/features_output_*.csv')
    fallback = 'output/final_combined_features_400series.csv'
    file_to_load = max(files, key=os.path.getctime) if files else fallback
    df = pd.read_csv(file_to_load)

    # Re-create edge condition exactly as in notebook
    # "edge_condition = df['flag_missing_data'] == True"
    # missing_data is df.isna().any(axis=1)
    df['flag_missing_data'] = df.isna().any(axis=1)
    edge_condition = df['flag_missing_data'] == True

    if 'V-01_total_interview_duration_ms' in df.columns:
        edge_condition = edge_condition | (df['V-01_total_interview_duration_ms'] <= 0)
        
    if 'T-03_rt_entropy' in df.columns:
        edge_condition = edge_condition | (df['T-03_rt_entropy'] == 0)

    edge_cases = df[edge_condition]

    report_path = os.path.join('output', 'audit_findings_report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Detailed Analysis of the Audit Findings (Edge Cases)\n\n")
        f.write(f"We identified {len(edge_cases)} specific cases that triggered the critical edge case rules in the notebook.\n\n")
        
        count = 1
        for idx, row in edge_cases.iterrows():
            interview_id = row.get('interview_id', f'Row {idx}')
            f.write(f"## Finding {count}: Interview ID `{interview_id}`\n")
            
            reasons = []
            missing_cols = row[row.isna()].index.tolist()
            if missing_cols:
                if len(missing_cols) > 5:
                    reasons.append(f"Missing Data in {len(missing_cols)} columns (e.g., {', '.join(missing_cols[:5])}...)")
                else:
                    reasons.append(f"Missing Data in columns: {', '.join(missing_cols)}")
                    
            if row.get('V-01_total_interview_duration_ms', 1) <= 0:
                reasons.append(f"Invalid duration: {row.get('V-01_total_interview_duration_ms')} ms (<= 0 implies log failure or instant completion)")
                
            if row.get('T-03_rt_entropy', 1) == 0:
                reasons.append("Zero statistical entropy (suggests uniformly spaced robotic input or zero variance)")
                
            for r in reasons:
                f.write(f"- 🔴 **Flag Trigger:** {r}\n")
                
            f.write("\n")
            count += 1

    print(f"Generated report at {report_path}")
except Exception as e:
    traceback.print_exc(file=sys.stdout)
