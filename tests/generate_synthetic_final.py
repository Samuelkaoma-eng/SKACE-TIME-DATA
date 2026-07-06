"""
Generate the canonical synthetic paradata suite plus ground-truth labels.

Usage
-----
# Default: save to data/synthetic/<timestamp>/
python tests/generate_synthetic_final.py

# Write to a specific directory without touching data/
python tests/generate_synthetic_final.py --output-dir data/workflow_validation/canonical_validation

# Overwrite the canonical data/ files explicitly
python tests/generate_synthetic_final.py --overwrite

# Reproducible run with custom seed
python tests/generate_synthetic_final.py --seed 99
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.test_adversarial import AdversarialDataGenerator


def main():
    parser = argparse.ArgumentParser(description="Generate the canonical synthetic paradata validation suite.")
    parser.add_argument(
        '--output-dir',
        help='Write surveycto.csv, odk.csv, and ground_truth_labels.csv to a specific directory',
    )
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Overwrite canonical data/surveycto.csv, data/odk.csv, and data/ground_truth_labels.csv',
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='RNG seed for reproducibility (default: 42)',
    )
    args = parser.parse_args()

    if args.overwrite and args.output_dir:
        raise ValueError("--overwrite and --output-dir cannot be used together")

    print(f"Generating canonical synthetic paradata suite (seed={args.seed})...")
    generator = AdversarialDataGenerator(seed=args.seed)

    if args.overwrite:
        os.makedirs('data', exist_ok=True)
        scto_path = 'data/surveycto.csv'
        odk_path = 'data/odk.csv'
        gt_path = 'data/ground_truth_labels.csv'
        print("  [WARNING] --overwrite is set. Canonical data/ files will be replaced.")
    elif args.output_dir:
        out_dir = args.output_dir
        os.makedirs(out_dir, exist_ok=True)
        scto_path = f'{out_dir}/surveycto.csv'
        odk_path = f'{out_dir}/odk.csv'
        gt_path = f'{out_dir}/ground_truth_labels.csv'
        print(f"  Output directory: {out_dir}")
    else:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        out_dir = f'data/synthetic/{ts}'
        os.makedirs(out_dir, exist_ok=True)
        scto_path = f'{out_dir}/surveycto.csv'
        odk_path = f'{out_dir}/odk.csv'
        gt_path = f'{out_dir}/ground_truth_labels.csv'
        print(f"  Output directory: {out_dir}")

    print("  Synthesizing SurveyCTO structures (12 interviews, 5 profiles)...")
    scto_df = generator.generate_adversarial_suite(is_odk=False)
    scto_df.to_csv(scto_path, index=False)
    print(f"  -> Saved {len(scto_df)} rows to {scto_path}")

    print("  Synthesizing ODK Collect structures (12 interviews, 5 profiles)...")
    odk_df = generator.generate_adversarial_suite(is_odk=True)
    odk_df.to_csv(odk_path, index=False)
    print(f"  -> Saved {len(odk_df)} rows to {odk_path}")

    gt_df = generator.build_combined_ground_truth_labels()
    gt_df.to_csv(gt_path, index=False)
    print(f"  -> Saved {len(gt_df)} ground-truth labels to {gt_path}")

    print("\nGeneration Complete.")
    print(f"  SurveyCTO: {scto_path}")
    print(f"  ODK:       {odk_path}")
    print(f"  Labels:    {gt_path}")
    print("\nNext step: run `python run_pipeline.py --inputs ...` pointing at these files.")

    return scto_path, odk_path, gt_path


if __name__ == "__main__":
    main()
