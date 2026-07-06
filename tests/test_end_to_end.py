"""
End-to-end integration test for the full SKACE-Time-Data pipeline.

This test:
  1. Generates synthetic raw logs (SurveyCTO + ODK)
  2. Runs the full pipeline (parse -> extract -> detect)
  3. Evaluates against ground-truth labels
  4. Asserts that precision >= 0.80 and recall >= 0.75 (thesis Section 5)
"""

import os
import shutil
import sys
import uuid
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.pipeline.controller import PipelineController
from tests.test_adversarial import AdversarialDataGenerator


# Ground truth must match test_adversarial.py profile mapping exactly.
GROUND_TRUTH = {
    # SurveyCTO
    "INT400": 0,
    "INT401": 1,
    "INT402": 1,
    "INT403": 1,
    "INT404": 1,
    "INT405": 0,
    "INT406": 0,
    "INT407": 1,
    "INT408": 1,
    "INT409": 1,
    "INT410": 1,
    "INT411": 1,
    # ODK
    "ODK400": 0,
    "ODK401": 1,
    "ODK402": 1,
    "ODK403": 1,
    "ODK404": 1,
    "ODK405": 0,
    "ODK406": 0,
    "ODK407": 1,
    "ODK408": 1,
    "ODK409": 1,
    "ODK410": 1,
    "ODK411": 1,
}

# Thesis Section 5 acceptance thresholds
PRECISION_THRESHOLD = 0.80
RECALL_THRESHOLD = 0.75


@pytest.fixture(scope="module")
def e2e_workdir():
    """Module-scoped temp dir under repo test_runtime_tmp/."""
    root = Path(__file__).resolve().parent.parent / "test_runtime_tmp"
    root.mkdir(exist_ok=True)
    workdir = root / f"e2e_{uuid.uuid4().hex}"
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        yield workdir
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@pytest.fixture(scope="module")
def pipeline_results(e2e_workdir):
    """Generate raw logs, run the full pipeline, and return the results DataFrame."""
    generator = AdversarialDataGenerator(seed=42)

    scto_df = generator.generate_adversarial_suite(is_odk=False)
    odk_df = generator.generate_adversarial_suite(is_odk=True)

    scto_path = e2e_workdir / "surveycto.csv"
    odk_path = e2e_workdir / "odk.csv"
    scto_df.to_csv(scto_path, index=False)
    odk_df.to_csv(odk_path, index=False)

    controller = PipelineController(parser_type="auto")
    return controller.process_batch([scto_path, odk_path])


class TestEndToEnd:
    def test_pipeline_returns_dataframe(self, pipeline_results):
        assert isinstance(pipeline_results, pd.DataFrame), "process_batch must return DataFrame"
        assert not pipeline_results.empty, "Pipeline returned empty DataFrame"

    def test_all_interviews_extracted(self, pipeline_results):
        found_ids = set(pipeline_results["interview_id"].astype(str))
        expected_ids = set(GROUND_TRUTH.keys())
        missing = expected_ids - found_ids
        assert not missing, f"Missing interviews in pipeline output: {missing}"

    def test_required_feature_columns_present(self, pipeline_results):
        required = [
            "T-01_rt_variance",
            "T-02_rt_iqr",
            "T-03_rt_entropy",
            "T-04_rt_skewness",
            "T-05_rt_kurtosis",
            "T-06_rt_mean",
            "T-07_rt_median",
            "T-08_rt_cv",
            "T-09_rt_min",
            "T-10_rt_max",
            "V-01_total_interview_duration_ms",
            "V-05_back_navigation_rate",
            "V-06_back_navigation_total_count",
            "V-07_time_of_day_hour",
            "V-10_zero_back_nav_flag",
            "anomaly_score",
            "anomaly_category",
            "is_anomalous",
        ]
        missing = [column for column in required if column not in pipeline_results.columns]
        assert not missing, f"Missing feature columns: {missing}"

    def test_anomaly_categories_are_valid(self, pipeline_results):
        valid_categories = {"normal", "suspicious", "anomalous", "dq_issue"}
        found_categories = set(pipeline_results["anomaly_category"].unique())
        invalid = found_categories - valid_categories
        assert not invalid, f"Unexpected anomaly categories: {invalid}"

    def test_normal_interviews_score_low(self, pipeline_results):
        """Normal interviews should have anomaly scores of 0 or 1."""
        normal_ids = [iid for iid, val in GROUND_TRUTH.items() if val == 0]
        normal_rows = pipeline_results[
            pipeline_results["interview_id"].astype(str).isin(normal_ids)
        ]
        if normal_rows.empty:
            pytest.skip("No normal interviews found in output")
        high_score_normals = normal_rows[normal_rows["anomaly_score"] > 1]
        assert len(high_score_normals) == 0, (
            "Normal interviews have unexpectedly high anomaly scores:\n"
            f"{high_score_normals[['interview_id', 'anomaly_category', 'anomaly_score']].to_string()}"
        )

    def test_fabricated_interviews_score_at_least_five(self, pipeline_results):
        fabricated_ids = ["INT401", "INT407", "ODK401", "ODK407"]
        fabricated_rows = pipeline_results[
            pipeline_results["interview_id"].astype(str).isin(fabricated_ids)
        ]
        if fabricated_rows.empty:
            pytest.skip("Fabricated interviews not found in output")
        low_score_fabricated = fabricated_rows[fabricated_rows["anomaly_score"] < 5]
        assert len(low_score_fabricated) == 0, (
            "Fabricated interviews did not meet the anomaly score contract:\n"
            f"{low_score_fabricated[['interview_id', 'anomaly_category', 'anomaly_score']].to_string()}"
        )

    def test_anomalous_interviews_score_above_zero(self, pipeline_results):
        """Anomalous interviews should have anomaly scores > 0."""
        anomalous_ids = [iid for iid, val in GROUND_TRUTH.items() if val == 1]
        anomalous_rows = pipeline_results[
            pipeline_results["interview_id"].astype(str).isin(anomalous_ids)
        ]
        if anomalous_rows.empty:
            pytest.skip("No anomalous interviews found in output")
        undetected = anomalous_rows[anomalous_rows["anomaly_score"] == 0]
        assert len(undetected) == 0, (
            "Anomalous interviews produced zero anomaly score:\n"
            f"{undetected[['interview_id', 'anomaly_category', 'anomaly_score']].to_string()}"
        )

    def test_precision_meets_threshold(self, pipeline_results):
        """Precision must be >= 0.80 as specified in thesis Section 5."""
        merged = pipeline_results.copy().assign(
            interview_id=pipeline_results["interview_id"].astype(str)
        )
        merged = merged.assign(gt=merged["interview_id"].map(GROUND_TRUTH))
        merged = merged.dropna(subset=["gt"])

        y_true = merged["gt"].values
        y_pred = (merged["anomaly_category"] != "normal").astype(int).values

        tp = np.sum((y_true == 1) & (y_pred == 1))
        fp = np.sum((y_true == 0) & (y_pred == 1))
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0

        assert precision >= PRECISION_THRESHOLD, (
            f"Precision {precision:.4f} is below the threshold {PRECISION_THRESHOLD}. "
            f"TP={tp}, FP={fp}"
        )

    def test_recall_meets_threshold(self, pipeline_results):
        """Recall must be >= 0.75 as specified in thesis Section 5."""
        merged = pipeline_results.copy().assign(
            interview_id=pipeline_results["interview_id"].astype(str)
        )
        merged = merged.assign(gt=merged["interview_id"].map(GROUND_TRUTH))
        merged = merged.dropna(subset=["gt"])

        y_true = merged["gt"].values
        y_pred = (merged["anomaly_category"] != "normal").astype(int).values

        tp = np.sum((y_true == 1) & (y_pred == 1))
        fn = np.sum((y_true == 1) & (y_pred == 0))
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

        assert recall >= RECALL_THRESHOLD, (
            f"Recall {recall:.4f} is below the threshold {RECALL_THRESHOLD}. "
            f"TP={tp}, FN={fn}"
        )

    def test_dq_issue_interviews_detected(self, pipeline_results):
        """DQ issue interviews should be classified as dq_issue."""
        dq_ids = ["INT402", "INT408", "INT409", "ODK402", "ODK408", "ODK409"]
        dq_rows = pipeline_results[
            pipeline_results["interview_id"].astype(str).isin(dq_ids)
        ]
        if dq_rows.empty:
            pytest.skip("DQ issue interviews not found in output")
        non_dq = dq_rows[dq_rows["anomaly_category"] != "dq_issue"]
        assert len(non_dq) == 0, (
            "DQ issue interviews were not classified as dq_issue:\n"
            f"{non_dq[['interview_id', 'anomaly_category', 'anomaly_score']].to_string()}"
        )

    def test_section_features_have_variance(self, pipeline_results):
        """Section-level variance should not collapse into a single pseudo-section."""
        if "S-03_within_section_variance" not in pipeline_results.columns:
            pytest.skip("S-03 column not in output")
        variance_of_variance = pipeline_results["S-03_within_section_variance"].var()
        assert variance_of_variance > 0, (
            "S-03_within_section_variance is constant across all interviews"
        )

    def test_statistical_features_are_dynamic(self, pipeline_results):
        """
        Verify that statistical features (T-series) actually vary across
        interviews and are not returning static values.
        """
        for col in ['T-01_rt_variance', 'T-03_rt_entropy', 'T-06_rt_mean']:
            if col in pipeline_results.columns:
                unique_count = pipeline_results[col].nunique()
                assert unique_count > 1, (
                    f"Feature {col} has only {unique_count} unique value(s) "
                    f"across {len(pipeline_results)} interviews; "
                    f"possible static output"
                )
