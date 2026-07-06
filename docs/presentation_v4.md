# Automated Extraction and Analysis of Timing-Based Paradata Features for Survey Quality Assurance

**Project Proposal Presentation**

Samuel Kaoma  
Computer Number: 2022016530  
Course: CSC 4004 - Project  
Supervisor: Mr. Mofya Phiri  
Date: 26th March 2026

---

## Agenda

- Introduction and Background
- Problem Statement and Objectives
- Literature Review
- Proposed Methodology
- Feature Taxonomy and Catalogue
- Anomaly Detection
- Tools and Technologies
- Evaluation and Validation
- Project Timeline and Risks
- Expected Outcomes
- Conclusion

---

## Abstract

- **Paradata Insights**: Valuable behavioral data from survey platforms, underutilized due to complexity
- **Project Goal**: Automated system for extracting timing-based features from SurveyCTO and ODK logs
- **Key Components**: Parsing, feature extraction (30+ indicators), statistical analysis, anomaly detection
- **Validation**: Synthetic datasets with injected anomalies, evaluated on precision/recall
- **Outcomes**: Python library, documentation, validation report – bridging theory to practice

---

## Introduction

- **Survey Quality Importance**: Critical for research, policy, and decision-making in health, economics, social sciences
- **Digital Platforms**: SurveyCTO and ODK enhance efficiency with automatic paradata recording
- **Paradata Definition**: Auxiliary data on interview conduct – timestamps, navigation, pauses, edits
- **Potential Benefits**: Detect rushed/fabricated responses, confusion, disengagement
- **Current Gap**: Underutilized due to format differences and lack of automated tools
- **Project Solution**: Platform-agnostic pipeline combining data engineering and statistical methods

---

## Problem Statement

- **Limitations of Current Methods**: Rely on simple metrics (e.g., total duration), miss behavioral irregularities
- **Issues Detected**: Rushed responses, inattentive navigation, fabricated data go undetected
- **Paradata Challenges**: Raw logs vary by platform (SurveyCTO: event-based CSV; ODK: different taxonomy)
- **Statistical Needs**: Methods must handle non-normal, skewed response time distributions
- **Barrier**: No automated, format-aware tools for scalable paradata analysis

---

## Objectives

1. **Literature Review**: Catalogue timing-based quality indicators and map to feature taxonomy
2. **Parser Development**: Create format-aware parsers for SurveyCTO/ODK into common representation
3. **Feature Extraction**: Implement 30-50 timing indicators across question/section/survey levels
4. **Statistical Measures**: Compute variance, entropy, skewness, kurtosis for distributions
5. **Anomaly Detection**: Use IQR thresholding and rules, validate on precision/recall
6. **Outputs**: Structured datasets, Python library, documentation for reuse

---

## Scope

**In Scope:**
- Audit log processing from SurveyCTO and ODK
- 30-50 timing/behavioral features
- Statistical characterization
- IQR/rule-based anomaly detection
- Synthetic validation with labelled anomalies
- Python library, format guide, output datasets

**Out of Scope:**
- Real-time monitoring
- External integrations/dashboards
- ML predictive models
- Primary data collection

---

## Literature Review

- **TSE Framework (Groves et al., 2009)**: Theoretical foundation for survey error sources
- **Paradata Quality (Couper, 1998)**: Process data as quality indicators in CASIC
- **Response Latency (Yan & Tourangeau, 2008)**: Complexity, age, familiarity predict timing; fast responses signal disengagement
- **Adaptive Design (Conrad et al., 2013)**: Pauses, back-navigation identify difficulty/disengagement
- **Fabrication Detection (Wenz et al., 2019)**: Compressed distributions, low back-navigation in fabricated interviews
- **Survey-Level Features (Kreuter, 2013)**: Duration, speed trajectory, time-of-day as robust indicators

---

## Proposed Methodology

- **Pipeline Overview**: Ingestion → Parsing → Feature Extraction → Characterization → Detection → Output
- **Modular Design**: Separation of parsing and extraction layers for platform agnosticism
- **Data Flow**: Raw logs → Platform parsers → Common Intermediate Representation (CIR) → Features
- **CIR Schema**: Pandas DataFrame with interview_id, field_name, event_type, timestamps, duration
- **Feature Levels**: Question (response time, edits), Section (pace, pauses), Survey (duration, navigation)
- **Statistical Layer**: Distributional measures (variance, IQR, entropy, skewness, kurtosis)

---

## Preliminary Feature Taxonomy

| Level | Category | Examples |
|-------|----------|----------|
| Question | Timing | Response time, time-to-first-interaction, edit count, revisit flag |
| Question | Patterns | Keystrokes, constraint triggers, idle time |
| Section | Pace/Flow | Mean pace, variance, section-to-section ratio |
| Section | Pauses | Pause counts (>5s, >30s), mean/max duration |
| Survey | Patterns | Total duration, speed trajectory, back-navigation rate |
| Survey | Temporal | Time-of-day, day-of-week, session vs. median |
| Statistical | Measures | Variance, IQR, entropy, skewness, kurtosis of response times |

---

## Feature Catalogue (40 Features)

**Question-Level (Q-01 to Q-10):**
- Q-01: response_time_ms – Total field time
- Q-02: time_to_first_interaction – Delay to first input
- Q-03: edit_count – Modifications before leaving
- Q-04: revisit_flag – Back-navigation indicator
- Q-05: revisit_count – Number of revisits
- Q-06: field_completion_ratio – Mandatory completion
- Q-07: idle_time_ms – Inactive periods
- Q-08: keystroke_count – Text input volume
- Q-09: constraint_trigger_count – Validation errors
- Q-10: first_to_last_interaction_duration – Input span

**Section-Level (S-01 to S-10):**
- S-01: mean_section_pace – Average question time
- S-02: section_duration_ms – Total section time
- S-03: within_section_variance – Timing spread
- S-04: section_to_section_pace_ratio – Relative pace
- S-05: pause_count_5s – Gaps >5s
- S-06: pause_count_30s – Gaps >30s
- S-07: mean_pause_duration_ms – Average pause length
- S-08: max_pause_duration_ms – Longest pause
- S-09: back_nav_count_section – Section back-navs
- S-10: section_completion_rate – Answered proportion

**Survey-Level (V-01 to V-10):**
- V-01: total_interview_duration_ms – Full interview time
- V-02: speed_trajectory_early – First quarter pace
- V-03: speed_trajectory_late – Final quarter pace
- V-04: speed_trajectory_ratio – Early/late ratio
- V-05: back_navigation_rate – Navs per question
- V-06: back_navigation_total_count – Total navs
- V-07: time_of_day_hour – Start hour
- V-08: day_of_week – Interview day
- V-09: session_length_vs_median – Relative duration
- V-10: zero_back_nav_flag – No navs >20 questions

**Statistical (T-01 to T-10):**
- T-01: rt_variance – Response time spread
- T-02: rt_iqr – Interquartile range
- T-03: rt_entropy – Distribution randomness
- T-04: rt_skewness – Asymmetry measure
- T-05: rt_kurtosis – Tailedness
- T-06: rt_mean – Average response time
- T-07: rt_median – Median response time
- T-08: rt_cv – Coefficient of variation
- T-09: rt_min – Minimum time
- T-10: rt_max – Maximum time

---

## Parser Design and Format Handling

- **Platform Differences**: SurveyCTO (event-based CSV, epoch ms); ODK (different taxonomy, ISO timestamps)
- **Class Hierarchy**: Base ParadataParser → SurveyCTOParser, ODKParser
- **Normalization**: Convert to common schema (interview_id, field_name, event_type, start_ms, end_ms, duration_ms)
- **Benefits**: Unified downstream processing, easy extension to new platforms
- **Implementation**: Pandas DataFrame for intermediate representation

---

## Anomaly Detection

- **Definition**: Statistically significant deviation in timing behavior
- **Criteria**: Extreme duration, low variance, no pauses/navs >20 questions, uniform fast responses
- **Methods**:
  - **IQR Thresholding**: Flag values outside 1.5*IQR from Q1/Q3 (robust to non-normality)
  - **Rule-Based**: Domain thresholds (e.g., zero back-nav >20 questions)
- **Why IQR?**: Handles skewed distributions better than Z-scores; no normality assumption
- **Scoring**: Proportional to flagged features per interview

---

## Tools and Technologies

- **Language**: Python 3.10+
- **Data Processing**: Pandas, NumPy
- **Statistics**: SciPy
- **Visualization**: Matplotlib, Seaborn
- **Development**: Jupyter Notebook, VS Code
- **Testing**: Pytest
- **Ethical**: Anonymized paradata, synthetic validation

---

## Evaluation Methodology

- **Feature Validation**: Mann-Whitney U tests for discriminative power; Cohen's d effect sizes
- **Detection Performance**: Precision (0.80 target), Recall (0.75 target), F1-score vs. labelled synthetic anomalies
- **Baselines**: Aggregate duration threshold; Single-feature rule
- **Cross-Format**: Robustness on SurveyCTO/ODK synthetic datasets
- **Synthetic Strategy**: Log-normal for times, Poisson for events; injected anomalies (fabrication, speeding, disengagement)

---

## Project Timeline

| Phase | Weeks | Activities |
|-------|-------|------------|
| Proposal | 1-2 | Planning, writing |
| Literature | 3-7 | Review, taxonomy |
| Design | 8-9 | Architecture |
| Parsers | 10-13 | Implementation, testing |
| Features | 14-18 | Extraction, stats |
| Detection | 19-21 | IQR, rules |
| Midway | 22 | Evaluation |
| Validation | 23-26 | Datasets, tests |
| Outputs | 27-29 | Docs, reports |
| Final | 30-31 | Paper writing |
| Submission | 32 | Deliverables |

---

## Risk Analysis

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Incomplete logs | Medium | Validation, error handling |
| Format changes | Low | Configurable mapping |
| Performance | Medium | Vectorized ops, chunking |
| Detection issues | Medium | Validation, tuning |
| Non-discriminative features | Low | Statistical tests, exclusion |

---

## Limitations

- Synthetic data may not fully capture real variability
- Thresholds may not generalize across contexts/populations
- Preliminary taxonomy; some features may be non-discriminative
- No real-world validation against known anomalies
- Class imbalance in synthetic datasets affects metrics

---

## Expected Outcomes

- **Python Library**: 30-50 features with docstrings
- **Format Guide**: SurveyCTO/ODK structures, parsing
- **Validation Dataset**: Synthetic with labelled anomalies
- **Report**: Precision/recall, effect sizes
- **Final Paper**: 5,000-7,000 words
- **Outputs**: Structured datasets, summaries, visualizations

---

## AI-Assisted Development

- **Tools**: GitHub Copilot, Claude, ChatGPT
- **Tasks**: Code generation, proofreading, API clarification
- **Validation**: Line-by-line review, unit testing
- **Transparency**: AI Usage Log maintained

---

## Conclusion

- **Impact**: Operationalize paradata for scalable survey quality assurance
- **Innovation**: Automated, platform-agnostic pipeline with robust detection
- **Validation**: Rigorous synthetic evaluation with baselines
- **Future**: Extend to real corpora, integrate ML if needed
- **Thank You! Questions?**

---

## References

1. Groves et al. (2009) - Survey Methodology
2. Couper (1998) - CASIC quality
3. Conrad et al. (2013) - Adaptive design
4. Kreuter (2013) - Paradata improvements
5. Yan & Tourangeau (2008) - Response times
6. Wenz et al. (2019) - Fabrication detection
7. Olson et al. (2018) - Cross-platform logs
8. McKinney (2017) - Python for Data Analysis
9. Hawkins (1980) - Outlier identification
10. Chandola et al. (2009) - Anomaly detection survey
11. Chawla et al. (2002) - SMOTE
12. Iglewicz & Hoaglin (1993) - Outliers
13. Hodge & Austin (2004) - Outlier methodologies
14. Japkowicz & Stephen (2002) - Class imbalance

*End of Presentation*