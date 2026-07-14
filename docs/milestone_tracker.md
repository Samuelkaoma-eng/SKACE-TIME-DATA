# Milestone Tracker, Automated Extraction and Analysis of Timing-Based Paradata Features for Survey Quality Assurance

Student: Samuel Kaoma (2022016530) · Course: CSC 4004 · Supervisor: Mr. Mofya Phiri
Repository: https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA (branch `main`)
Proposal date: 26 March 2026 · Last verified: 6 July 2026 (32/32 tests passing; robustness round on held-out seeds: precision 0.96–1.00, recall 0.84–1.00, all runs above the proposal thresholds)

Commit links use the short hash; full history is on the [commits page](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/commits/main).

## Work Plan Status

| # | Phase (Proposal §6) | Planned Weeks | Status | Evidence and commits |
|---|---------------------|---------------|--------|----------------------|
| 1 | Proposal and Planning | 1–2 | Done | `docs/deliverables/SAMUEL KAOMA 2022016530 V4.pdf` (submitted proposal, 26 March 2026); source files `docs/Samuel_Kaoma 2022016530_para data proposal.docx`, [`docs/revised_proposal.md`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/blob/main/docs/revised_proposal.md) |
| 2 | Literature Review and Feature Cataloguing | 3–7 | Done | Proposal §2 (Tables 1–3, 40-feature catalogue); [`docs/feature_documentation.md`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/blob/main/docs/feature_documentation.md), commits [`37ae029`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/commit/37ae029) (first version), [`cad8b7a`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/commit/cad8b7a) (final) |
| 3 | System Design | 8–9 | Done | Modular pipeline in [`src/`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/tree/main/src): parsers → CIR → features → validation → controller, commits [`fe89e7f`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/commit/fe89e7f) (skeleton), [`37ae029`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/commit/37ae029) (architecture) |
| 4 | Parser Development (SurveyCTO + ODK) | 10–13 | Done | [`src/parsers/`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/tree/main/src/parsers), unit tests in `tests/test_parsers.py`, commits [`37ae029`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/commit/37ae029) (both parsers), [`54ff5c7`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/commit/54ff5c7) (mixed-file handling), [`c82fd96`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/commit/c82fd96) (timestamp parsing repair) |
| 5 | Feature Extraction Implementation (30–50 features) | 14–18 | Done | All 40 catalogued features (Q/S/V/T) in [`src/features/`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/tree/main/src/features); tests in `tests/test_features.py`, commits [`37ae029`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/commit/37ae029) (initial modules), [`96f44db`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/commit/96f44db) (full 40 with thesis alignment), [`36ce869`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/commit/36ce869) (granular question/section exports) |
| 6 | Anomaly Detection (IQR + rule-based) | 19–21 | Done | [`src/validation/anomaly_detector.py`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/blob/main/src/validation/anomaly_detector.py), config in `detector_config.py`, commits [`2f91436`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/commit/2f91436), [`96f44db`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/commit/96f44db) (detector), [`84cae63`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/commit/84cae63) (config wiring), [`7bb265d`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/commit/7bb265d) (de-tuning + elevated-pause rule) |
| 7 | Midway Evaluation (supervisor checkpoint) | 22 | In progress | Progress report prepared: [`docs/progress_report_week16.md`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/blob/main/docs/progress_report_week16.md) |
| 8 | Synthetic Dataset Generation and Validation | 23–26 | Done | Generator `tests/test_adversarial.py` + `tests/generate_benchmark_datasets.py`; labelled datasets in [`data/generated_benchmarks/`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/tree/main/data/generated_benchmarks), commits [`0d399cb`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/commit/0d399cb) (validation suite), [`6716ab7`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/commit/6716ab7) (labelled evaluation), [`42bae73`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/commit/42bae73) (benchmark generator), [`7bb265d`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/commit/7bb265d) (realism upgrade + held-out robustness round: [`output/robustness_validation/robustness_summary.md`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/blob/main/output/robustness_validation/robustness_summary.md)) |
| 9 | Output and Documentation | 27–29 | Done | [`docs/feature_documentation.md`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/blob/main/docs/feature_documentation.md), [`docs/paradata_format_guide.md`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/blob/main/docs/paradata_format_guide.md), structured outputs in `output/`, commits [`5370dac`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/commit/5370dac), [`cad8b7a`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/commit/cad8b7a) |
| 10 | Final Report Writing (5,000–7,000 words) | 30–31 | Done | `docs/deliverables/SAMUEL KAOMA 2022016530 Final Report.docx` and `.pdf` (5,556 words, Harvard referencing, includes robustness results); markdown source in `report/final_academic_report.md`. Note: the file previously labelled V4 is the submitted proposal, not a report draft |
| 11 | Final Submission | 32 | Not yet due | Code + report + presentation (`docs/deliverables/Kaoma_Paradata_Presentation.pptx`) |

## Expected Outcomes (Proposal §4), Deliverable Check

| Deliverable | Status | Location |
|-------------|--------|----------|
| Python feature library, 30–50 features, documented | 40 features | [`src/features/`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/tree/main/src/features), `docs/feature_library_usage.md` |
| Paradata format guide (SurveyCTO + ODK) | Done | [`docs/paradata_format_guide.md`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/blob/main/docs/paradata_format_guide.md), `docs/deliverables/Paradata_Format_Guide.docx` |
| Synthetic validation dataset with injected anomalies + labels | Done | [`data/generated_benchmarks/`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/tree/main/data/generated_benchmarks), `docs/deliverables/Synthetic_Validation_Datasets/` |
| Validation report (precision, recall, effect sizes) | Done | [`output/robustness_validation/robustness_summary.md`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/blob/main/output/robustness_validation/robustness_summary.md), `output/final_validation_report.md`, `docs/validation_report.md` |
| Final paper 5,000–7,000 words | Complete | `docs/deliverables/SAMUEL KAOMA 2022016530 Final Report.docx` (+ PDF) |
| Structured output dataset + statistical summaries + visualizations | Done | [`output/`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/tree/main/output) |
| AI Usage Log appendix (Proposal §9.4) | Started | [`docs/ai_usage_log.md`](https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA/blob/main/docs/ai_usage_log.md), maintain through to submission |

## Progress Review Checkpoints

Counting from the proposal (Week 1 ≈ 23 March 2026):

- **Week 8 review** ≈ mid-May 2026.
- **Week 16 review** ≈ 6–12 July 2026. Progress report: `docs/progress_report_week16.md`.
- **Week 24 review** ≈ early September 2026.
