import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
import pytest
from pathlib import Path

# Assume parsers are correctly imported
from src.parsers.surveycto_parser import parse_surveycto_audit
from src.parsers.odk_parser import parse_odk_audit

def test_surveycto_parser_empty_file(tmp_path):
    # Setup mock CSV
    p = tmp_path / "empty_audit.csv"
    p.write_text("event,node,start,end\n")
    
    df = parse_surveycto_audit(p)
    assert isinstance(df, pd.DataFrame)
    assert df.empty

def test_surveycto_parser_valid_data(tmp_path):
    # Setup mock CSV
    p = tmp_path / "valid_audit.csv"
    p.write_text("event,node,start,end\nQuestion,q1,1600000000000,1600000001000\n")
    
    df = parse_surveycto_audit(p)
    assert not df.empty
    assert 'duration_ms' in df.columns
    assert df.iloc[0]['duration_ms'] == 1000.0

def test_odk_parser_iso_timestamps_convert_to_epoch_ms(tmp_path):
    # ISO 8601 timestamps must convert to epoch milliseconds regardless of the
    # internal datetime resolution used by the installed pandas version.
    p = tmp_path / "iso_audit.csv"
    p.write_text(
        "event,node,start,end\n"
        "question,q1,2026-03-01T09:00:00.000Z,2026-03-01T09:00:01.500Z\n"
    )

    df = parse_odk_audit(p)
    assert df.iloc[0]['start_ms'] == 1772355600000.0
    assert df.iloc[0]['end_ms'] == 1772355601500.0
    assert df.iloc[0]['duration_ms'] == 1500.0

def test_odk_parser_missing_field_names_use_placeholder(tmp_path):
    # Regression: blank ODK names were converted to the literal string "nan"
    # instead of the unknown_field placeholder, which then leaked into the
    # section features as a pseudo-question.
    p = tmp_path / "blank_name_audit.csv"
    p.write_text(
        "instance_id,name,event,start_time,end_time\n"
        "uuid-1,,form start,2026-03-01T09:00:00.000Z,2026-03-01T09:00:01.000Z\n"
        "uuid-1,household_q01,question,2026-03-01T09:00:02.000Z,2026-03-01T09:00:05.000Z\n"
    )

    df = parse_odk_audit(p)
    assert df.iloc[0]['field_name'] == 'unknown_field'
    assert 'nan' not in set(df['field_name'].str.lower())
    assert df.iloc[1]['field_name'] == 'household_q01'

def test_odk_parser_negative_duration(tmp_path):
    p = tmp_path / "neg_audit.csv"
    # End time is before start time
    p.write_text("event,node,start,end\nQuestion,q1,1600000001000,1600000000000\n")

    df = parse_odk_audit(p)
    assert pd.isna(df.iloc[0]['duration_ms'])

def test_native_odk_audit_log_is_detected_and_administrative_rows_excluded(tmp_path):
    # ODK's documented audit log has event/node/start/end columns with epoch
    # millisecond timestamps, which look like a SurveyCTO export. It must be
    # routed to the ODK parser by its event vocabulary, and its form-level
    # events must not become a pseudo-section.
    from src.features.question_features import QuestionFeatureExtractor
    from src.features.section_features import SectionFeatureExtractor
    from src.pipeline.controller import PipelineController

    p = tmp_path / "audit.csv"
    p.write_text(
        "event,node,start,end\n"
        "form start,,1672646400000,\n"
        "question,/data/household/q01,1672646401000,1672646406000\n"
        "question,/data/household/q02,1672646406500,1672646414000\n"
        "jump,,1672646414500,1672646416000\n"
        "question,/data/health/q03,1672646420000,1672646431000\n"
        "end screen,,1672646431500,1672646433000\n"
        "form save,,1672646433000,\n"
        "form exit,,1672646433100,\n"
    )

    cir = PipelineController(parser_type='auto')._parse_to_cir(p)
    assert set(cir['event_type']) >= {'form_start', 'field_start', 'form_end'}
    assert 'form save' not in set(cir['event_type'])

    q = QuestionFeatureExtractor().extract(cir)
    sections = SectionFeatureExtractor().extract(cir, q)
    assert set(sections.index) == {'household', 'health'}
    assert 'MainSection' not in sections.index

def test_one_history_parses_identically_from_both_formats(tmp_path):
    # Parser equivalence can only be claimed if both formats carry the same
    # interviews, so one generated history is rendered into both and the
    # intermediate representations are compared row for row.
    from tests.test_adversarial import AdversarialDataGenerator

    generator = AdversarialDataGenerator(seed=3, difficulty="stress")
    plan = generator.build_benchmark_plan(dataset_size=20, anomaly_ratio=0.3)
    surveycto_df, odk_df = generator.generate_paired_benchmark(plan)

    reference = AdversarialDataGenerator(seed=3, difficulty="stress")
    reference_plan = reference.build_benchmark_plan(dataset_size=20, anomaly_ratio=0.3)
    pd.testing.assert_frame_equal(
        surveycto_df, reference.generate_benchmark_suite(plan=reference_plan, is_odk=False)
    )

    scto_path, odk_path = tmp_path / "scto.csv", tmp_path / "odk.csv"
    surveycto_df.to_csv(scto_path, index=False)
    odk_df.to_csv(odk_path, index=False)
    scto_cir = parse_surveycto_audit(scto_path).reset_index(drop=True)
    odk_cir = parse_odk_audit(odk_path).reset_index(drop=True)

    assert len(scto_cir) == len(odk_cir)
    for column in ['interview_id', 'field_name', 'start_ms', 'end_ms', 'duration_ms']:
        pd.testing.assert_series_equal(
            scto_cir[column], odk_cir[column], check_dtype=False, check_names=False
        )
