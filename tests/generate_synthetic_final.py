import os
import sys
sys.path.append(os.path.abspath('.'))

from tests.test_adversarial import AdversarialDataGenerator

def main():
    print("Generating Academic Paradata Synthetic Audit Suite...")
    generator = AdversarialDataGenerator()
    os.makedirs('data', exist_ok=True)
    
    # Generate SurveyCTO representation
    print(" Synthesizing SurveyCTO structures...")
    scto_df = generator.generate_adversarial_suite(is_odk=False)
    scto_path = 'data/surveycto.csv'
    scto_df.to_csv(scto_path, index=False)
    print(f" -> Saved to {scto_path}")

    # Generate ODK Collect representation
    print(" Synthesizing ODK Collect structures...")
    odk_df = generator.generate_adversarial_suite(is_odk=True)
    odk_path = 'data/odk.csv'
    odk_df.to_csv(odk_path, index=False)
    print(f" -> Saved to {odk_path}")

    print("\nGeneration Complete. Pipeline is ready to run via `python run_pipeline.py`.")

if __name__ == "__main__":
    main()
