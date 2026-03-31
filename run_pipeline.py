import os
import sys
import argparse
from pathlib import Path
from typing import List, Union

from src.pipeline.controller import PipelineController


def process_interview(filepath: Union[str, Path], parser_type: str = 'auto') -> List[dict]:
    """
    Public API wrapper: process a single paradata file and return a list of
    per-interview feature dictionaries.

    Used by test_pipeline.py and any external caller that needs a simple
    functional interface without instantiating PipelineController directly.

    Parameters
    ----------
    filepath : str or Path
        Path to the raw audit log CSV.
    parser_type : str
        One of 'auto', 'surveycto', 'odk'. Default = 'auto'.

    Returns
    -------
    List[dict]
        One dictionary per interview found in the file.
    """
    controller = PipelineController(parser_type=parser_type)
    return controller.process_file(filepath)

def interactive_cli(data_dir: Path):
    """Provide an interactive CLI to select a dataset if multiple exist."""
    print("=== Paradata Feature Extraction Pipeline ===")
    
    csv_files = list(data_dir.glob("*.csv"))

    if not csv_files:
        print(f"No CSV files found in '{data_dir.absolute()}'.")
        print("Please place your audit logs into the 'data/' directory.")
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
    parser = argparse.ArgumentParser(description="Run the academic paradata pipeline.")
    parser.add_argument("--data-dir", default="data", help="Raw audit log directory")
    parser.add_argument("--output-dir", default="output", help="Features output directory")
    parser.add_argument("--parser", default="auto", choices=["auto", "surveycto", "odk"], help="Parser type")
    parser.add_argument("--interactive", action="store_true", help="Launch interactive UI")
    
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    
    data_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if args.interactive or len(sys.argv) == 1:
        csv_files = interactive_cli(data_dir)
        if not csv_files:
            return 0
    else:
        csv_files = list(data_dir.glob("*.csv"))
        if not csv_files:
            print(f"No CSV files found in '{data_dir.absolute()}'.")
            return 0
            
    print(f"\nInitializing Pipeline Controller with config: Parser = {args.parser.upper()}")
    controller = PipelineController(parser_type=args.parser)
    
    print(f"Beginning Batch Processing for {len(csv_files)} files...")
    final_df = controller.process_batch(csv_files)
    
    if final_df.empty:
        print("No features extracted. Pipeline failed or data was invalid.")
        return 1
        
    # Standardize output naming
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"features_output_{timestamp}.csv"
    
    # Save output
    final_df.to_csv(output_file, index=False, na_rep='NaN')
    
    print(f"\n Features engineered for {len(final_df)} extracted interviews.")
    print("Anomaly Detection Rules (IQR + Entropy + Speed) successfully applied.")
    print(f"Structured dataset written to: {output_file.absolute()}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
