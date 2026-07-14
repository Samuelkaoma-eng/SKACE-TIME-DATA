# Progress Report, Week 8 Review

**Project:** Automated Extraction and Analysis of Timing-Based Paradata Features for Survey Quality Assurance  
**Student:** Samuel Kaoma (2022016530) · **Course:** CSC 4004 · **Supervisor:** Mr. Mofya Phiri  
**Repository:** https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA (branch `main`)  
**Checkpoint date:** Week 8, mid-May 2026 (prepared retrospectively in July 2026 from the repository history, because the Week 8 review itself was missed; the content describes the project as it stood in mid-May)  

## 1. What I have built so far

Implementation started immediately after the proposal was accepted and moved faster than the proposal timeline anticipated. By mid-May the core pipeline existed end to end rather than only the design and parser work that the plan scheduled for Weeks 8 to 13:

- Parsers for both platforms (`src/parsers/`). A shared base class defines the Common Intermediate Representation (interview identifier, field name, event type, start and end in epoch milliseconds, duration), and the SurveyCTO and ODK subclasses handle each platform's column names, event vocabulary and timestamp encoding. The controller auto-detects which format a file is in and can split files where rows from both platforms were merged into a single export.
- The feature library (`src/features/`). All 40 features from the proposal catalogue (Q-01 to Q-10, S-01 to S-10, V-01 to V-10, T-01 to T-10) are implemented in four modules by granularity.
- Anomaly detection (`src/validation/`). Interview-level detection combining IQR fences on key timing features with rule-based checks (minimum plausible duration, low entropy, uniform pacing, zero back-navigation), producing a transparent per-interview score and category.
- Synthetic data and evaluation. A labelled synthetic generator produces benchmark packs at n=500, 2,000 and 10,000 interviews in both formats, and a labelled evaluation path merges predictions with ground truth to compute precision and recall.
- A pytest suite covering parsers, features, the detector and the end-to-end pipeline, plus a generated audit notebook that walks through a full run.
- A repair round in April fixed timestamp parsing edge cases (epoch seconds versus milliseconds versus ISO 8601 strings) found while testing the ODK path.

## 2. How this maps to my objectives

| Objective from proposal | Status at Week 8 | Where |
|---|---|---|
| 1. Catalogue timing features from the literature | Done | Proposal §2, Tables 1 to 3 |
| 2. Parsers for SurveyCTO and ODK with a common format | Done | `src/parsers/` |
| 3. Extract 30 to 50 features at three granularities | Done (40) | `src/features/` |
| 4. Statistical measures (variance, entropy, skewness, kurtosis) | Done | `src/features/statistical_features.py` |
| 5. IQR + rule-based detection, validated on labelled data | Built; validation ongoing | `src/validation/` |
| 6. Output datasets, feature docs, format guide | Started | `output/`, early drafts in `docs/` |

Detection results on the synthetic packs at this point scored precision 1.00 and recall 1.00. I did not yet appreciate how suspicious those perfect scores should have been; revisiting the separability of the synthetic data was later scheduled for the validation phase.

## 3. Blockers

- The Week 8 review meeting itself did not happen on schedule, which is why this summary was reconstructed afterwards.
- No real labelled paradata was available, so all evaluation is synthetic, as scoped in the proposal.
- Documentation (format guide, feature documentation) lagged behind the code at this stage.

## 4. Next steps (Weeks 9 to 16)

1. Harden the labelled evaluation workflow and recalibrate detector thresholds against the synthetic packs.
2. Write up the paradata format guide and feature documentation to match the implemented behaviour.
3. Scrutinise the perfect validation scores: make the generator harder and re-evaluate on data the detector was not tuned to.
4. Begin drafting the final report chapters alongside the validation work.
