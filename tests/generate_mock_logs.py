import pandas as pd
import numpy as np
import os
from datetime import datetime, timezone

def generate_mock_logs():
    os.makedirs('data', exist_ok=True)
    
    # 1. SurveyCTO format (millisecond epoch timestamps)
    scto_data = []
    base_time = 1700000000000 # epoch ms
    
    # Normal Interview
    for i in range(1, 11):
        scto_data.append({
            'interview_id': 'INT_NORMAL',
            'node': f'q{i}',
            'event': 'question-start' if i == 1 else 'question-end',
            'start': base_time + (i * 10000),
            'end': base_time + (i * 10000) + 5000,
            'duration_ms': 5000
        })
        
    # Speeding Interview (very fast)
    for i in range(1, 11):
        scto_data.append({
            'interview_id': 'INT_SPEEDER',
            'node': f'q{i}',
            'event': 'question-end',
            'start': base_time + (i * 100),
            'end': base_time + (i * 100) + 50,
            'duration_ms': 50
        })
        
    pd.DataFrame(scto_data).to_csv('data/surveycto.csv', index=False)
    print("Generated data/surveycto.csv")

    # 2. ODK format (ISO 8601 timestamps)
    odk_data = []
    base_dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Normal Interview
    for i in range(1, 11):
        start_dt = pd.Timestamp(base_dt) + pd.Timedelta(seconds=i*10)
        end_dt = start_dt + pd.Timedelta(seconds=5)
        odk_data.append({
            'instance_id': 'ODK_NORMAL',
            'name': f'q{i}',
            'event': 'question-end',
            'start_time': start_dt.isoformat(),
            'end_time': end_dt.isoformat()
        })
        
    pd.DataFrame(odk_data).to_csv('data/odk.csv', index=False)
    print("Generated data/odk.csv")

if __name__ == '__main__':
    generate_mock_logs()
