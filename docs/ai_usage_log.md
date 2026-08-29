# AI Usage Log, Appendix

**Project:** Automated Extraction and Analysis of Timing-Based Paradata Features for Survey Quality Assurance
**Student:** Samuel Kaoma (2022016530) - **Course:** CSC 4004 - **Supervisor:** Mr. Mofya Phiri

Required by section 9.4 of the project proposal. The log records where software tools were consulted during the project. It was started on 6 July 2026, so entries before that date are reconstructed from the development history and are marked as reconstructed.

## Summary of use

Tool support was limited to in-editor suggestions, debugging discussion, review comments, and help checking or polishing documentation. The research question, feature taxonomy, system design, parser structure, anomaly-detection approach, thresholds used in `main`, validation interpretation, and final academic claims are my own work.

All accepted code-level suggestions were reviewed before integration and checked through the project test suite or by comparison with recorded output files. Suggestions that affected the interpretation of results or detection thresholds were treated as review input only; final decisions were made by me and, where relevant, kept out of the submitted `main` branch.

## Work carried out by the student

- Research question, proposal, literature review, and the 40-feature taxonomy.
- Common intermediate representation for SurveyCTO and ODK paradata.
- Parser classes, feature extraction modules, pipeline controller, and labelled evaluation workflow.
- Choice of IQR-based and rule-based anomaly detection, including thresholds shipped in `main`.
- Synthetic data generator, anomaly profiles, stress-validation setup, and success criteria.
- Interpretation of validation results and the decision to report weaker per-class results transparently.

## Log entries

| Date | Tool | Use | How it affected the submitted work |
|---|---|---|---|
| Mar 2026 (reconstructed) | GitHub Copilot | In-editor suggestions while writing parser and DataFrame code | Used only for small line-level completions. Logic was written, reviewed, and tested by me. |
| Mar 2026 (reconstructed) | Claude | Discussion of IQR fences and modified z-score methods | Used for clarification while writing the proposal rationale. The chosen method and citations were checked and written by me. |
| Mar-Apr 2026 (reconstructed) | Claude | Debugging discussion for timestamp parsing across epoch and ISO formats | Helped identify a possible guard for epoch seconds. I implemented and tested the parser behaviour. |
| Apr 2026 (reconstructed) | ChatGPT | Discussion of labelled evaluation structure | Used as a check on avoiding label leakage. The validation reporting code was written by me. |
| 6 Jul 2026 | Claude | Review comments on `src/` and generator realism | Used as review input. I fixed confirmed issues, removed generator-specific tuning, and verified the changes on held-out seeds. |
| 6-14 Jul 2026 | Claude | Drafting support for progress documentation and clean-run checks | Draft text was edited by me. The clean-run checks surfaced defects that I fixed and covered with tests. |
| 19 Aug 2026 | Claude | Evidence-link and reproducibility checks | Used to help check links, tags, and reported figures against repository files and regenerated outputs. Corrections were reviewed by me before finalising. |
| 19-25 Aug 2026 | Claude | Validation-documentation review | Helped identify missing aggregate figures, baseline figures, effect sizes, and per-component breakdowns. Values were recomputed from existing project outputs and checked by me. |
| 19-25 Aug 2026 | Claude | Bounded diagnostic discussion on fabricated false negatives | Used on development seeds only. The submitted `main` branch was not changed by this diagnostic; the attempted threshold adjustment remained on a separate branch and was not merged. |
| 25 Aug 2026 | Claude | Consistency review of final report, Word deliverables, and presentation | Used to locate stale or contradictory wording. Corrections were made against recorded outputs and reviewed by me. |
