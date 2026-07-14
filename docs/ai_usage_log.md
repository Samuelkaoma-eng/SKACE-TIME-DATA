# AI Usage Log, Appendix

**Project:** Automated Extraction and Analysis of Timing-Based Paradata Features for Survey Quality Assurance  
**Student:** Samuel Kaoma (2022016530) · **Course:** CSC 4004 · **Supervisor:** Mr. Mofya Phiri  

Required by §9.4 of the project proposal. Each entry records the tool, the date, the task, what came back, and how much of it was used. This log was started on 6 July 2026, later than it should have been; entries before that date are reconstructed from the development history and are marked as such. It is maintained live from 6 July 2026 onward.

## How AI was used in this project

Three tools were used, matching §9.1 of the proposal: GitHub Copilot (in-editor completions), Claude (code review, documentation drafting, debugging discussion), and ChatGPT (occasional design discussion). Per §9.2–9.3, AI-assisted code was reviewed before integration and is covered by the pytest suite; the feature taxonomy, the choice of detection method, and the interpretation of results are my own, grounded in the sources cited in the proposal.

## Log entries

| Date | Tool | Task / prompt summary | Output and how it was used |
|---|---|---|---|
| Mar 2026 (reconstructed) | GitHub Copilot | In-editor completions while writing parser classes and Pandas transformations | Accepted line-level completions for boilerplate (column mapping, DataFrame construction); logic reviewed and unit-tested (`tests/test_parsers.py`) |
| Mar 2026 (reconstructed) | Claude | Explanation of IQR fences vs modified Z-score for skewed distributions | Used to sharpen the §3.3 justification; text rewritten in my own words with citations checked against Iglewicz & Hoaglin |
| Mar–Apr 2026 (reconstructed) | Claude | Debugging assistance on timestamp parsing (epoch-ms vs epoch-seconds vs ISO 8601) | Suggested the median-based epoch-seconds guard; implemented after tracing through sample values, covered by parser tests (commit `15b8258`) |
| Apr 2026 (reconstructed) | ChatGPT | Discussion of how to structure labelled evaluation without leaking labels into detection | Confirmed the ground-truth merge design; implementation written by me in `src/validation/reporting.py` |
| 6 Jul 2026 | Claude | Line-by-line review of all modules in `src/` against the proposal specification | Found two defects (integrity flag overwritten by the detector; ODK missing node names becoming the string "nan") and several proposal/code mismatches. Both defects fixed and re-tested (commit `bc77a8c`); mismatches noted for report revision |
| 6 Jul 2026 | Claude | Review of synthetic generator realism and detector tuning | Identified generator-specific detector tuning (pause constants, back-nav coupling). I approved removing the coupling, moving constants into configuration, and adding a median-relative elevated-pause rule from Conrad et al.'s disengagement indicators. Verified by held-out runs (seeds 7, 99) documented in `output/robustness_validation/robustness_summary.md` (commit `bc77a8c`) |
| 6 Jul 2026 | Claude | Drafting of progress report, checkpoint guide, milestone tracker and this log's structure | Drafts generated, then reviewed and edited by me; factual claims (metrics, commit hashes, file paths) checked against the repository |
| 14 Jul 2026 | Claude | Final pre-submission audit: clean-environment reproduction of every documented command, regeneration of all synthetic datasets from recorded seeds, and reconciliation of every number in the report and documentation against the fresh runs | Found and fixed two code defects (a pandas 3 timestamp-resolution incompatibility in both parsers that scaled ODK durations wrongly on a fresh install, and the Q-01 response-time feature duplicating Q-10 instead of matching its documented definition), added a parser regression test, corrected citation years and feature formulas in the documentation, and rebuilt the Word deliverables and presentation from the reconciled sources. All fixes reviewed by me and verified by the test suite and regenerated validation runs |
