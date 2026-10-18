"""The results site must explain every flag the detector can raise, in words.

The detector emits flag names only. scripts/build_results_site.py restates each
rule as a sentence and as a row of a rules table. These tests fail if the
detector gains, loses or re-scores a flag without the site being updated, so
the page cannot silently drift from the detector.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import build_results_site as site  # noqa: E402
from src.validation.anomaly_detector import AnomalyDetector  # noqa: E402


def detector_flags():
    d = AnomalyDetector
    return d.RULE_FLAG_COLUMNS + d.IQR_FLAG_COLUMNS + d.DATA_QUALITY_FLAG_COLUMNS


def test_every_flag_has_a_plain_language_explanation():
    detector = AnomalyDetector()
    batch = {name: 1.0 for name, _, _ in site.KEY_FEATURES}
    batch.update({"S-03_within_section_variance": 1.0, "fence_V-01": (0.0, 1.0),
                  "fence_T-06": (0.0, 1.0), "fence_T-03": (0.0, 1.0)})
    for flag in detector_flags():
        kind, label, text = site.explain(flag, {}, batch, detector)
        assert label != flag, f"{flag} has no explanation in scripts/build_results_site.py"
        assert kind in {"rule", "iqr", "dq"}
        assert text and text != flag


def test_rules_table_covers_exactly_the_detectors_flags():
    rules = site.rules_table(AnomalyDetector())
    assert sorted(r["flag"] for r in rules) == sorted(detector_flags())


def test_rules_table_scoring_matches_the_detector():
    scored = {r["flag"] for r in site.rules_table(AnomalyDetector()) if r["scored"]}
    expected = set(AnomalyDetector.SCORED_FLAG_COLUMNS) | set(AnomalyDetector.IQR_FLAG_COLUMNS)
    assert scored == expected


def test_rules_table_kinds_match_the_detector_groups():
    kinds = {r["flag"]: r["kind"] for r in site.rules_table(AnomalyDetector())}
    for flag in AnomalyDetector.DATA_QUALITY_FLAG_COLUMNS:
        assert kinds[flag] == "dq"
    for flag in AnomalyDetector.IQR_FLAG_COLUMNS:
        assert kinds[flag] == "iqr"
    for flag in AnomalyDetector.RULE_FLAG_COLUMNS:
        assert kinds[flag] == "rule"


def test_feature_catalogue_lists_forty_features_in_four_families():
    catalogue = site.feature_catalogue()
    assert len(catalogue) == 40
    assert len({c["id"] for c in catalogue}) == 40
    for family in "QSVT":
        assert sum(c["family"] == family for c in catalogue) == 10
