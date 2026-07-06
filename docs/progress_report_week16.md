# Progress Report — Week 16 Review

**Project:** Automated Extraction and Analysis of Timing-Based Paradata Features for Survey Quality Assurance
**Student:** Samuel Kaoma (2022016530) · **Course:** CSC 4004 · **Supervisor:** Mr. Mofya Phiri
**Repository:** https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA (branch `main`)
**Date:** 6 July 2026

## 1. What I have built so far

The pipeline described in my proposal is working end to end. It takes raw audit logs from SurveyCTO or ODK, converts them into a common intermediate format, computes 40 timing features per interview, and flags suspicious interviews using IQR thresholds plus a set of rules (entropy floor, minimum plausible duration, zero back-navigation).

The main components are:

- Parsers for both platforms (`src/parsers/`). A base `ParadataParser` class holds the shared logic and the two subclasses handle each platform's format. The pipeline can also auto-detect which format a file is in, since in practice files sometimes get mixed together.
- The feature library (`src/features/`). All 40 features from the catalogue in my proposal (Q-01 to T-10) are implemented, split into question, section, survey and statistical modules. Usage is documented in `docs/feature_documentation.md` and `docs/feature_library_usage.md`.
- Anomaly detection (`src/validation/`). Thresholds live in a config file rather than being hard-coded, and I recalibrated them against the synthetic data (`scripts/threshold_recalibration.py`).
- Synthetic test data. A generator (`tests/generate_synthetic_final.py`) produces labelled datasets with injected anomalies at n=500, 2,000 and 10,000 in both formats. These are in `docs/deliverables/Synthetic_Validation_Datasets/`.
- Tests. 32 pytest tests covering the parsers, features, detector and full pipeline. All passing as of 6 July 2026.

## 2. How this maps to my objectives

| Objective from proposal | Status | Where |
|---|---|---|
| 1. Catalogue timing features from the literature | Done | Proposal §2, Tables 1–3 |
| 2. Parsers for SurveyCTO and ODK with a common format | Done | `src/parsers/`, `tests/test_parsers.py` |
| 3. Extract 30–50 features at three granularities | Done (40) | `src/features/` |
| 4. Statistical measures (variance, entropy, skewness, kurtosis) | Done | `src/features/statistical_features.py` |
| 5. IQR + rule-based detection, validated on labelled data | Done | `output/robustness_validation/robustness_summary.md` |
| 6. Output datasets, feature docs, format guide | Done | `output/`, `docs/paradata_format_guide.md` |

Early validation runs scored a perfect precision 1.00 and recall 1.00, which I treated as a warning sign rather than a result: the injected anomalies were too cleanly separated from normal behavior. I therefore ran a harder round in July. The generator was made more realistic (form-level events, per-question complexity weighting, constraint violations), detector settings that only made sense for the old generator were removed, and evaluation moved to seeds never used during development, including a stress mode where normal and anomalous distributions overlap and a class-imbalance sweep from 5% to 30% anomalies. Results: precision 0.96–1.00 and recall 0.84–1.00 across all runs, still above the 0.80/0.75 success criteria. Speeding is always detected; subtle fabrication is the hardest case (about 0.76), consistent with the known limitation of univariate IQR methods stated in the proposal. Full methodology and numbers: `output/robustness_validation/robustness_summary.md`. Mann-Whitney U tests found 28 of the 40 features significantly separate normal from anomalous interviews (`output/feature_validation_results.txt`).

Compared to the timeline in the proposal, I am ahead on implementation: the build phases (design, parsers, features, detection) were finished earlier than planned, and the time since has gone into validation runs at larger scales, documentation, and a first full draft of the report (about 5,550 words, in `docs/deliverables/`).

## 3. Blockers

- I missed the Week 8 review and I am submitting this late progress summary to catch up. My apologies for that.
- The AI Usage Log required by §9.4 of my proposal was not kept as I went. It now exists (`docs/ai_usage_log.md`) with earlier entries reconstructed from the development history and marked as such; it is maintained live from 6 July onward.
- No real labelled paradata was available, so evaluation is synthetic-only as scoped in the proposal. This limits external validity and I flag it in the report.

## 4. Next steps (Weeks 17–24)

1. Keep the AI Usage Log current.
2. Act on feedback from this review.
3. Revise the report draft into the final 5,000–7,000 word version, incorporating the July robustness results and the discussion of missed subtle-fabrication cases.
4. Investigate whether a simple multivariate score (for example, count of co-occurring weak signals) can lift fabrication recall without hurting precision, as future-work material.
5. Prepare for the Week 24 review and the final presentation.
