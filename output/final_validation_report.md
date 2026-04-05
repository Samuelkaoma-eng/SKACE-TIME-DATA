# Final Validation Report

## Status

The current pipeline passes the strict end-to-end examiner audit and the local
automated test suite.

- `pytest`: `24 passed`
- Examiner audit: `PASS`

Primary artifacts:
- `output/examiner_audit/strict_examiner_audit_report.md`
- `output/examiner_audit/strict_examiner_audit_report.json`

## Verified Contract

For the canonical `n500` benchmark packs:

- SurveyCTO: precision `1.0000`, recall `1.0000`, F1 `1.0000`
- ODK: precision `1.0000`, recall `1.0000`, F1 `1.0000`
- Fabricated interviews scoring `>= 5`: `33 / 33`
- Normal interviews scoring `<= 1`: `400 / 400`

For the `n10000` SurveyCTO scale pack:

- precision `1.0000`
- recall `1.0000`
- runtime ratio versus `n500`: `19.87`

## Examiner Reproducibility Checks

The strict examiner audit verifies:

- raw file columns match the documented format guide
- SurveyCTO and ODK timestamps match their documented formats
- both parsers emit the documented CIR schema
- sampled CIR durations equal `end_ms - start_ms`
- selected features can be recomputed manually from the raw logs
- anomaly scores can be reconstructed from the flagged feature columns
- status labels match the scoring rules
- fabricated interviews exhibit compressed timing, low entropy, and low back-navigation
- baseline methods underperform the full detector
- cross-format performance remains consistent

## Baseline Comparison

On `n500` SurveyCTO:

- Duration-IQR baseline: precision `1.0000`, recall `0.6600`
- Zero-back-nav baseline: precision `0.5455`, recall `0.6600`
- Full detector: precision `1.0000`, recall `1.0000`

## Conclusion

Proposal v4, the format guide, the current feature library, the feature outputs,
and the anomaly reports are now aligned on the refreshed synthetic benchmark
packs. The strict examiner path is reproducible from raw logs to final metrics.
