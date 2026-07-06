# Progress Review Checkpoints, What To Do

Project: Automated Extraction and Analysis of Timing-Based Paradata Features for Survey Quality Assurance
Student: Samuel Kaoma (2022016530) · CSC 4004 · Supervisor: Mr. Mofya Phiri
Repository: https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA

Reviews fall around Weeks 8, 16 and 24, counted from Week 1 ≈ 23 March 2026. Every review is submitted through the same project portal used for the proposal. The expected package each time: the repository link plus a one to two page progress summary covering four things, what has been built, how it maps to the objectives, current blockers, and next steps. A short demo or slides are optional.

---

## Week 8 review (was due ≈ mid-May 2026), MISSED, submit late

Do these in order:

1. Email Mr. Phiri before touching the portal. Keep it short: you missed the Week 8 checkpoint, you take responsibility, the late summary and the Week 16 report are both going into the portal this week. Ask whether he wants anything else attached.
2. Submit the late Week 8 summary below through the portal, marked clearly as a late submission.
3. Include the repository link.

### Week 8 summary (ready to paste, edit anything that does not sound like you)

> **Progress summary, Week 8 (submitted late)**
>
> **What was built by Week 8.** By mid-May the core system was already working: parsers for SurveyCTO and ODK audit logs feeding a shared intermediate format, the full 40-feature extraction library across question, section, survey and statistical levels, and the first version of the IQR-plus-rules anomaly detector. Unit tests covered the parsers and features.
>
> **Mapping to objectives.** Objectives 2 (format-aware parsers), 3 (30–50 features) and 4 (statistical measures) were complete at this point. Objective 1 (literature-derived catalogue) was done in the proposal itself. Objectives 5 (validated detection) and 6 (documentation and outputs) were in progress.
>
> **Blockers at the time.** None technical. The reason this report is late is poor scheduling discipline on my part, I concentrated on building and did not submit the checkpoint. I have set reminders for the remaining reviews.
>
> **Next steps from Week 8.** Labelled synthetic validation, threshold calibration, documentation, and the report draft. (These have since been completed, see the Week 16 report.)

---

## Week 16 review (due ≈ 6–12 July 2026), DUE NOW

1. Make sure the latest work is pushed to GitHub so the links in the report resolve.
2. Submit `docs/progress_report_week16.md` through the portal (paste the text or export it to PDF, whichever the portal takes).
3. Include the repository link: https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA
4. Optional: attach `docs/deliverables/Kaoma_Paradata_Presentation.pptx`.
5. If the portal allows one attachment only, the report is the attachment and the repo link goes in the comment field.

The Week 16 report already covers the four required parts: built work, objective mapping, blockers (missed Week 8, AI log started late, synthetic-only evaluation), next steps.

---

## Week 24 review (due ≈ early September 2026), PREPARE

What should be true by then, so plan backwards:

- Final report revised to match the current system, including the robustness results (held-out seeds, stress difficulty, imbalance sweep) and honest discussion of the misses on subtle fabrication.
- AI usage log (`docs/ai_usage_log.md`) up to date.
- Presentation rehearsed once.

### Week 24 report skeleton (fill the bracketed parts when the time comes)

> **Progress summary, Week 24**
>
> **What has been built.** The complete pipeline: dual-format parsers, 40-feature library, configurable IQR-plus-rules detector, labelled synthetic benchmark generator, and a validation suite covering held-out seeds, stress-difficulty data and class-imbalance sweeps. [Add anything new since Week 16.]
>
> **How it maps to the objectives.** All six proposal objectives are implemented and validated. Held-out results: precision 0.96–1.00, recall 0.84–1.00, above the 0.80/0.75 success criteria. [Update numbers if re-run.]
>
> **Blockers.** [State honestly. If none: report writing is the remaining work and it is on schedule.]
>
> **Next steps.** Final report consolidation, presentation, and submission package for Week 32: code repository, report PDF, presentation, AI usage log appendix.

---

## Final submission (Week 32), checklist

- [ ] Report PDF, 5,000–7,000 words, matching the actual system
- [ ] Repository link, final commit pushed and tagged (`git tag v1.0 && git push origin v1.0`)
- [ ] Presentation file
- [ ] AI usage log appendix
- [ ] Ground-truth datasets and instructions to reproduce results (`README.md` covers the commands)
