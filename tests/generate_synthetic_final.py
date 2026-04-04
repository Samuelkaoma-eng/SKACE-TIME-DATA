"""
tests/generate_synthetic_final.py
==================================
Generates the 400-series adversarial synthetic paradata suite plus ground truth.

Usage
-----
# Default: save to data/synthetic/ with timestamp
python tests/generate_synthetic_final.py

# Overwrite the canonical data/ files
python tests/generate_synthetic_final.py --overwrite

# Reproducible run with custom seed
python tests/generate_synthetic_final.py --seed 99
"""

import argparse
import os
import sys
from datetime import datetime

sys.path.append(os.path.abspath('.'))

from tests.test_adversarial import AdversarialDataGenerator


def main():
    parser = argparse.ArgumentParser(description="Generate adversarial synthetic paradata suite.")
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

    print(f"Generating Academic Paradata Synthetic Audit Suite (seed={args.seed})...")
    generator = AdversarialDataGenerator(seed=args.seed)

    if args.overwrite:
        os.makedirs('data', exist_ok=True)
        scto_path = 'data/surveycto.csv'
        odk_path = 'data/odk.csv'
        gt_path = 'data/ground_truth_labels.csv'
        print("  [WARNING] --overwrite is set. Canonical data/ files will be replaced.")
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
