import os
import sys
import argparse
import pandas as pd
import numpy as np
from pathlib import Path

# 1. Correctly import from src.features and src.parsers
from src.parsers.surveycto_parser import parse_surveycto_audit
from src.parsers.odk_parser import parse_odk_audit
from src.features.response_time import calculate_basic_timing, calculate_speed_index
from src.features.pauses import calculate_pauses
from src.features.navigation import calculate_navigation_metrics
from src.features.rhythm import calculate_rhythm_metrics

def process_interview(file_path: Path, parser_type: str = 'surveycto') -> list:
    """Process an interview paradata file and extract features per interview."""
    # 2. Load the dataset correctly
    if parser_type == 'surveycto':
        df = parse_surveycto_audit(file_path)
    else:
        df = parse_odk_audit(file_path)
        
    if df.empty:
        return [{'file_name': file_path.name, 'error': 'Empty or invalid file'}]
        
    features_list = []
    
    # Group by interview_id if it exists, else treat the whole file as one interview
    if 'interview_id' in df.columns:
        groups = df.groupby('interview_id')
    else:
        groups = [("unknown_interview", df)]
        
    for interview_id, group_df in groups:
        # Extract features
        basic_timing = calculate_basic_timing(group_df)
        pauses = calculate_pauses(group_df)
        nav = calculate_navigation_metrics(group_df)
        rhythm = calculate_rhythm_metrics(group_df)
        
        # 3. Merge feature outputs correctly into a single dictionary
        features = {
            'file_name': file_path.name,
            'interview_id': interview_id,
            **basic_timing,
            **pauses,
            **nav,
            **rhythm
        }
        features_list.append(features)
        
    return features_list

def interactive_cli(data_dir: Path):
    """Provide an interactive CLI to select a dataset if multiple exist."""
    print("=== Paradata Feature Extraction Pipeline ===")
    
    csv_files = list(data_dir.glob("*.csv"))
    
    if not csv_files:
        print(f"No CSV files found in '{data_dir.absolute()}'.")
        print("Please place your audit logs in this directory and run again.")
        return None
        
    print("\nAvailable datasets:")
    for idx, file_path in enumerate(csv_files, 1):
        print(f"  {idx}. {file_path.name}")
        
    while True:
        try:
            choice = input(f"\nSelect dataset to process (1-{len(csv_files)}) or 'all': ").strip()
            if choice.lower() == 'all':
                return csv_files
            
            idx = int(choice)
            if 1 <= idx <= len(csv_files):
                return [csv_files[idx-1]]
            else:
                print(f"Invalid choice. Please enter a number between 1 and {len(csv_files)}.")
        except ValueError:
            print("Invalid input. Please enter a number or 'all'.")

def main():
    parser = argparse.ArgumentParser(description="Run the paradata feature extraction pipeline.")
    parser.add_argument("--data-dir", default="data", help="Directory containing raw audit CSV logs")
    parser.add_argument("--output-dir", default="output", help="Directory to save final feature outputs")
    parser.add_argument("--parser", default="surveycto", choices=["surveycto", "odk"], help="Parser format to use")
    parser.add_argument("--interactive", action="store_true", help="Launch interactive CLI")
    
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    
    # Ensure directories exist
    data_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if args.interactive or len(sys.argv) == 1:
        # Default to interactive if no args provided
        csv_files = interactive_cli(data_dir)
        if not csv_files:
            return 0
    else:
        csv_files = list(data_dir.glob("*.csv"))
        if not csv_files:
            print(f"No CSV files found in '{data_dir.absolute()}'.")
            return 0
            
    # Timestamped output to prevent overwriting
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"features_output_{timestamp}.csv"
    
    all_features = []
    
    print(f"Found {len(csv_files)} files to process...")
    for file_path in csv_files:
        print(f"Processing: {file_path.name}")
        features_list = process_interview(file_path, args.parser)
        all_features.extend(features_list)
        
    if all_features:
        final_df = pd.DataFrame(all_features)
        
        # Calculate speed index across the dataset (requires global median)
        if 'total_duration_ms' in final_df.columns:
            median_duration = final_df['total_duration_ms'].median()
            final_df['speed_index'] = final_df['total_duration_ms'].apply(
                lambda x: calculate_speed_index(x, median_duration) if pd.notna(x) else np.nan
            )
            
        # 4. Calculate Robust Anomaly Scores (IQR Method)
        # Survey timing data is highly skewed, so naive Z-scores are inappropriate.
        # We use Interquartile Range (IQR) for robust outlier detection.
        if len(final_df) > 1:
            final_df['is_anomalous'] = 0
            
            # Robust bounds for Total Duration
            if 'total_duration_ms' in final_df.columns:
                Q1_dur = final_df['total_duration_ms'].quantile(0.25)
                Q3_dur = final_df['total_duration_ms'].quantile(0.75)
                IQR_dur = Q3_dur - Q1_dur
                
                # Severe outliers are > Q3 + 3*IQR or < Q1 - 3*IQR
                final_df.loc[final_df['total_duration_ms'] > (Q3_dur + 3 * IQR_dur), 'is_anomalous'] = 1
                final_df.loc[final_df['total_duration_ms'] < (Q1_dur - 3 * IQR_dur), 'is_anomalous'] = 1
                
            # Straightlining is generally an absolute bad behavior indicator, 
            # but we can look for statistical outliers as well.
            if 'straightlining_count' in final_df.columns:
                Q3_str = final_df['straightlining_count'].quantile(0.75)
                IQR_str = Q3_str - final_df['straightlining_count'].quantile(0.25)
                # If straightlining is abnormally high
                final_df.loc[final_df['straightlining_count'] > (Q3_str + 3 * IQR_str), 'is_anomalous'] = 1
                
        # 5. Save the final dataset
        final_df.to_csv(output_file, index=False)
        print(f"\nSuccess! Extracted features for {len(all_features)} interviews.")
        print(f"Final dataset saved to: {output_file.absolute()}")
    else:
        print("No features were extracted.")
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
