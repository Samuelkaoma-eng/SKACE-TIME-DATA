# Progress Report, Week 24 Review

**Project:** Automated Extraction and Analysis of Timing-Based Paradata Features for Survey Quality Assurance  
**Student:** Samuel Kaoma (2022016530) · **Course:** CSC 4004 · **Supervisor:** Mr. Mofya Phiri  
**Repository:** https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA (branch `main`)  
**Checkpoint date:** Week 24, early September 2026 (summary prepared in advance during the July pre-submission audit; it describes the completed state of the project entering the final submission phase)  

## 1. What I have built

The system is complete and verified end to end in a clean environment. Since the Week 16 review the work has been consolidation rather than new construction: a full pre-submission audit was run in a fresh virtual environment, every synthetic dataset was regenerated from its recorded seed, every documented command was re-executed, and every number in the report was re-derived from those fresh runs.

The audit mattered. Installing from `requirements.txt` on a clean machine pulls pandas 3, under which the parsers' timestamp conversion silently produced ODK durations a thousand times too small; the conversion was rewritten to be independent of the library's internal datetime resolution and a regression test was added. A second defect found during reconciliation was that the question-level response time feature (Q-01) had drifted from its documented definition and duplicated another feature (Q-10); it was reimplemented as documented. The test suite now stands at 33 tests, all passing.

The verified deliverable set is:

- The Python feature library (`src/features/`), 40 documented features across question, section, survey and statistical levels.
- Format-aware parsers with auto-detection and hybrid-file splitting (`src/parsers/`, `src/pipeline/controller.py`).
- The transparent anomaly detector with configurable thresholds (`src/validation/`).
- The paradata format guide, feature documentation, and feature library usage guide (`docs/`), each shipped as a Word deliverable.
- Labelled synthetic validation datasets at n=500, 2,000 and 10,000 in both platform formats (`data/synthetic_datasets/`, mirrored in `docs/deliverables/Synthetic_Validation_Datasets/`), plus a ready-to-run 24-interview sample in `data/`.
- The validation report and the reproducible robustness round (`scripts/run_robustness_validation.py`).
- The final paper, within the 5,000 to 7,000 word requirement, reconciled against the fresh runs.

## 2. How this maps to my objectives

| Objective from proposal | Status | Where |
|---|---|---|
| 1. Catalogue timing features from the literature | Done | Proposal §2, Tables 1 to 3; report §2 |
| 2. Parsers for SurveyCTO and ODK with a common format | Done | `src/parsers/`, verified on both formats and hybrid files |
| 3. Extract 30 to 50 features at three granularities | Done (40) | `src/features/`, all 40 present in every feature dataset |
| 4. Statistical measures (variance, entropy, skewness, kurtosis) | Done | `src/features/statistical_features.py` (T-01 to T-10) |
| 5. IQR + rule-based detection, validated on labelled data | Done | Robustness round: precision 0.95 to 1.00, recall 0.84 to 1.00 on held-out seeds, above the 0.80/0.75 criteria |
| 6. Output datasets, feature docs, format guide | Done | `output/`, `docs/`, Word copies in `docs/deliverables/` |

Reconciled evaluation highlights: the class imbalance sweep holds recall 1.00 from five to thirty percent prevalence with precision no worse than 0.96; the held-out stress runs score precision 0.9570 to 1.0000 and recall 0.80 to 0.90 across both formats; speeding is always caught, disengagement in 89 percent of stress instances, and subtle fabrication in 70 percent, the known univariate limit discussed in the report. Thirty of the forty features are statistically discriminative under Mann-Whitney U tests with Bonferroni correction.

## 3. Blockers

- None outstanding for submission. The remaining risk is environmental: the audit showed how easily a dependency major-version change can silently corrupt results, which is now mitigated by the regression test and the documented clean-environment verification procedure.
- Evaluation remains synthetic-only, as scoped; access to real labelled paradata is still the main limitation on external validity.

## 4. Next steps (Weeks 25 to 32)

1. Presentation rehearsal against the prepared deck (`docs/deliverables/Kaoma_Paradata_Presentation.pptx`).
2. Keep the AI Usage Log current through submission.
3. Final packaging check against the proposal's Expected Outcomes table in the milestone tracker, then submit in Week 32.
