import pandas as pd
from pathlib import Path
from sklearn.metrics import precision_score, recall_score, f1_score
from src.pipeline.controller import PipelineController

root = Path('c:/Users/Samuel/Desktop/4th year/Final year project/SKACE-Time-Data')
base = root / 'data' / 'synthetic_datasets'

controller = PipelineController()

for d in sorted(base.iterdir()):
    if not d.is_dir():
        continue
    print(f'=== {d.name} ===')
    gt = pd.read_csv(d / 'ground_truth_labels.csv')
    gt_dict = dict(zip(gt['interview_id'].astype(str), gt['is_anomalous'].astype(int)))
    for filename in ['audit_logs_odk.csv', 'audit_logs_surveycto.csv']:
        csv_path = d / filename
        if not csv_path.exists():
            continue
        df = controller.process_batch([str(csv_path)])
        df = df[df['interview_id'].astype(str).isin(gt_dict)]
        if df.empty:
            print(filename, 'NO MATCHING INTERVIEWS')
            continue
        df['is_anomalous_gt'] = df['interview_id'].astype(str).map(gt_dict)
        y_true = df['is_anomalous_gt'].astype(int)
        y_pred = df['is_anomalous'].astype(int)
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        print(f'{filename}: N={len(df)}, Precision={precision:.4f}, Recall={recall:.4f}, F1={f1:.4f}')
    print()
