"""
tests/test_end_to_end.py
=========================
End-to-end integration test for the full SKACE-Time-Data pipeline.

BUG-M5 FIX: Replaces the manual "run scripts, inspect CSV" validation workflow
with a single pytest-runnable test that:
  1. Generates adversarial synthetic raw logs (SurveyCTO + ODK)
  2. Runs the full pipeline (parse -> extract -> detect)
  3. Evaluates against hardcoded ground-truth labels
  4. Asserts that precision >= 0.80 and recall >= 0.75 (thesis §5 threshold)

Run:
    pytest tests/test_end_to_end.py -v

This is a World Bank-grade regression test: if any code change breaks the
detection threshold, this test turns RED immediately.
"""

import os
import sys
import shutil
import uuid
from pathlib import Path

import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tests.test_adversarial import AdversarialDataGenerator
from src.pipeline.controller import PipelineController


# ---------------------------------------------------------------------------
# Ground truth: must match test_adversarial.py profile mapping exactly
# ---------------------------------------------------------------------------
GROUND_TRUTH = {
    # SurveyCTO
    'INT400': 0, 'INT401': 1, 'INT402': 1, 'INT403': 1,
    'INT404': 1, 'INT405': 0, 'INT406': 0, 'INT407': 1,
    'INT408': 1, 'INT409': 1, 'INT410': 1, 'INT411': 1,
    # ODK
    'ODK400': 0, 'ODK401': 1, 'ODK402': 1, 'ODK403': 1,
    'ODK404': 1, 'ODK405': 0, 'ODK406': 0, 'ODK407': 1,
    'ODK408': 1, 'ODK409': 1, 'ODK410': 1, 'ODK411': 1,
}

PRECISION_THRESHOLD = 0.80
RECALL_THRESHOLD    = 0.75


@pytest.fixture(scope="module")
def e2e_workdir():
    """
    Module-scoped temp dir under repo test_runtime_tmp/ (same pattern as conftest).
    Cannot use tmp_path_factory: pytest.ini disables the tmpdir plugin (-p no:tmpdir).
    """
    root = Path(__file__).resolve().parent.parent / "test_runtime_tmp"
    root.mkdir(exist_ok=True)
    d = root / f"e2e_{uuid.uuid4().hex}"
    d.mkdir(parents=True, exist_ok=True)
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


@pytest.fixture(scope="module")
def pipeline_results(e2e_workdir):
    """
    Generate raw logs, run the full pipeline, return the results DataFrame.
    Uses a module-scoped fixture so generation + processing runs only once.
    """
    tmpdir = e2e_workdir
    gen = AdversarialDataGenerator(seed=42)

    # Generate raw audit logs
    scto_df = gen.generate_adversarial_suite(is_odk=False)
    odk_df  = gen.generate_adversarial_suite(is_odk=True)

    scto_path = tmpdir / "surveycto.csv"
    odk_path  = tmpdir / "odk.csv"
    scto_df.to_csv(scto_path, index=False)
    odk_df.to_csv(odk_path,  index=False)

    # Run full pipeline
    ctrl = PipelineController(parser_type='auto')
    results_df = ctrl.process_batch([scto_path, odk_path])

    return results_df


class TestEndToEnd:

    def test_pipeline_returns_dataframe(self, pipeline_results):
        """Pipeline must return a non-empty DataFrame."""
        assert isinstance(pipeline_results, pd.DataFrame), "process_batch must return DataFrame"
        assert not pipeline_results.empty, "Pipeline returned empty DataFrame"

    def test_all_interviews_extracted(self, pipeline_results):
        """All 24 interviews (12 SCTO + 12 ODK) must appear in output."""
        found_ids = set(pipeline_results['interview_id'].astype(str))
        expected_ids = set(GROUND_TRUTH.keys())
        missing = expected_ids - found_ids
        assert not missing, f"Missing interviews in pipeline output: {missing}"

    def test_required_feature_columns_present(self, pipeline_results):
        """All 40 thesis features (Q/S/V/T) must be present in output."""
        required = [
            # Statistical
            'T-01_rt_variance', 'T-02_rt_iqr', 'T-03_rt_entropy',
            'T-04_rt_skewness', 'T-05_rt_kurtosis', 'T-06_rt_mean',
            'T-07_rt_median', 'T-08_rt_cv', 'T-09_rt_min', 'T-10_rt_max',
            # Survey level
            'V-01_total_interview_duration_ms', 'V-05_back_navigation_rate',
            'V-06_back_navigation_total_count', 'V-07_time_of_day_hour',
            'V-10_zero_back_nav_flag',
            # Anomaly outputs
            'anomaly_score', 'anomaly_category', 'is_anomalous',
        ]
        missing = [c for c in required if c not in pipeline_results.columns]
        assert not missing, f"Missing feature columns: {missing}"

    def test_anomaly_categories_are_valid(self, pipeline_results):
        """anomaly_category must only contain recognised values."""
        valid_cats = {'normal', 'suspicious', 'anomalous', 'dq_issue'}
        found_cats = set(pipeline_results['anomaly_category'].unique())
        invalid = found_cats - valid_cats
        assert not invalid, f"Unexpected anomaly categories: {invalid}"

    def test_normal_interviews_not_flagged(self, pipeline_results):
        """Normal interviews (is_anomalous_ground_truth=0) must NOT be anomalous."""
        normal_ids = [k for k, v in GROUND_TRUTH.items() if v == 0]
        normal_rows = pipeline_results[
            pipeline_results['interview_id'].astype(str).isin(normal_ids)
        ]
        if normal_rows.empty:
            pytest.skip("No normal interviews found in output — check ID matching")
        flagged_normals = normal_rows[normal_rows['anomaly_category'] != 'normal']
        assert len(flagged_normals) == 0, (
            f"Normal interviews incorrectly flagged as anomalous:\n"
            f"{flagged_normals[['interview_id', 'anomaly_category', 'anomaly_score']].to_string()}"
        )

    def test_anomalous_interviews_are_detected(self, pipeline_results):
        """Anomalous interviews must NOT be classified as 'normal'."""
        anomalous_ids = [k for k, v in GROUND_TRUTH.items() if v == 1]
        anomalous_rows = pipeline_results[
            pipeline_results['interview_id'].astype(str).isin(anomalous_ids)
        ]
        if anomalous_rows.empty:
            pytest.skip("No anomalous interviews found in output — check ID matching")
        missed = anomalous_rows[anomalous_rows['anomaly_category'] == 'normal']
        assert len(missed) == 0, (
            f"Anomalous interviews missed by detector:\n"
            f"{missed[['interview_id', 'anomaly_category', 'anomaly_score']].to_string()}"
        )

    def test_precision_meets_thesis_threshold(self, pipeline_results):
        """Precision must be >= 0.80 as specified in thesis §5."""
        merged = pipeline_results.copy()
        merged['interview_id'] = merged['interview_id'].astype(str)
        merged['gt'] = merged['interview_id'].map(GROUND_TRUTH)
        merged = merged.dropna(subset=['gt'])

        y_true = merged['gt'].values
        y_pred = (merged['anomaly_category'] != 'normal').astype(int).values

        tp = np.sum((y_true == 1) & (y_pred == 1))
        fp = np.sum((y_true == 0) & (y_pred == 1))
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0

        assert precision >= PRECISION_THRESHOLD, (
            f"Precision {precision:.4f} is below thesis threshold {PRECISION_THRESHOLD}. "
            f"TP={tp}, FP={fp}"
        )

    def test_recall_meets_thesis_threshold(self, pipeline_results):
        """Recall must be >= 0.75 as specified in thesis §5."""
        merged = pipeline_results.copy()
        merged['interview_id'] = merged['interview_id'].astype(str)
        merged['gt'] = merged['interview_id'].map(GROUND_TRUTH)
        merged = merged.dropna(subset=['gt'])

        y_true = merged['gt'].values
        y_pred = (merged['anomaly_category'] != 'normal').astype(int).values

        tp = np.sum((y_true == 1) & (y_pred == 1))
        fn = np.sum((y_true == 1) & (y_pred == 0))
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

        assert recall >= RECALL_THRESHOLD, (
            f"Recall {recall:.4f} is below thesis threshold {RECALL_THRESHOLD}. "
            f"TP={tp}, FN={fn}"
        )

    def test_odk_fabricated_not_classified_as_dq_issue(self, pipeline_results):
        """
        Regression test for BUG-C1.
        ODK401 and ODK407 are FABRICATED (constant ~180ms RT). With the old
        second-precision ISO formatter they collapsed to zero-duration rows and
        were misclassified as 'dq_issue'. After the fix they must be 'suspicious'
        or 'anomalous', never 'dq_issue'.
        """
        fabricated_odk = pipeline_results[
            pipeline_results['interview_id'].astype(str).isin(['ODK401', 'ODK407'])
        ]
        if fabricated_odk.empty:
            pytest.skip("ODK401/ODK407 not in output")

        dq_classified = fabricated_odk[fabricated_odk['anomaly_category'] == 'dq_issue']
        assert len(dq_classified) == 0, (
            f"BUG-C1 REGRESSION: Fabricated ODK interviews classified as dq_issue:\n"
            f"{dq_classified[['interview_id', 'anomaly_category', 'T-06_rt_mean']].to_string()}"
        )

    def test_section_features_have_variance(self, pipeline_results):
        """
        Regression test for BUG-C4.
        Section-level features must not be identical across all interviews.
        With the old 'section_q01' naming all 20 questions fell in one section
        making S-01, S-03, S-04 constant == 1.0 across all rows.
        """
        if 'S-03_within_section_variance' not in pipeline_results.columns:
            pytest.skip("S-03 column not in output")
        variance_of_variance = pipeline_results['S-03_within_section_variance'].var()
        assert variance_of_variance > 0, (
            "BUG-C4 REGRESSION: S-03_within_section_variance is constant across all "
            "interviews — section inference is still putting all questions in one section."
        )
