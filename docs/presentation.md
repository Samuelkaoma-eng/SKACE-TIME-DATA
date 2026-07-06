# Automated Extraction and Analysis of Timing-Based Paradata Features for Survey Quality Assurance

**Project Proposal Presentation**

Samuel Kaoma  
Computer Number: 2022016530  
Course: CSC 4004 - Project  
Supervisor: Mr. Mofya Phiri  
Date: 24th March 2026

---

## Agenda

- Introduction and Background
- Problem Statement
- Objectives and Scope
- Literature Review
- Proposed Methodology
- Feature Taxonomy and Detection
- Evaluation and Timeline
- Risks and Limitations
- Conclusion

---

## Introduction

- **Paradata**: Auxiliary data from survey platforms capturing behavioral insights
- **Platforms**: SurveyCTO and ODK generate event-level timestamps, navigation, pauses
- **Potential**: Detect rushed responses, confusion, fabrication
- **Challenge**: Raw logs vary by platform; underutilized due to complexity
- **Aim**: Automated pipeline for timing-based feature extraction and anomaly detection

---

## Problem Statement

- Current quality assurance relies on simple metrics (e.g., total duration)
- Fails to capture behavioral irregularities at scale
- Platform-specific log formats hinder cross-platform analysis
- Statistical methods need robustness for non-normal timing data
- Gap: Lack of automated tools for paradata operationalization

---

## Objectives

1. Review timing-based quality indicators from literature
2. Develop parsers for SurveyCTO and ODK logs
3. Implement 30-50 timing-based features
4. Compute statistical measures (variance, entropy, etc.)
5. Implement IQR-based and rule-based anomaly detection
6. Generate structured outputs and documentation

---

## Scope

**In Scope:**
- SurveyCTO and ODK log processing
- 30-50 timing features
- Statistical characterization
- Anomaly detection (IQR + rules)
- Synthetic validation

**Out of Scope:**
- Real-time monitoring
- External integrations
- ML models
- Primary data collection

---

## Literature Review

- **TSE Framework**: Groves et al. (2009) - Error sources in surveys
- **Paradata Quality**: Couper (1998), Kreuter (2013)
- **Timing Indicators**: Yan & Tourangeau (2008) - Response latency
- **Fabrication Detection**: Wenz et al. (2019) - Compressed distributions
- **Adaptive Design**: Conrad et al. (2013) - Pauses and navigation
- **Key Findings**: 40 features mapped to survey methodology

---

## Proposed Methodology

- **Pipeline**: Ingestion → Parsing → Feature Extraction → Characterization → Detection → Output
- **Parsers**: Base class + SurveyCTO/ODK subclasses
- **Intermediate Representation**: Standardized DataFrame
- **Tools**: Python (Pandas, SciPy), Jupyter, VS Code
- **Ethical**: Anonymized data, synthetic validation

---

## Preliminary Feature Taxonomy

- **Question-Level**: Response time, time-to-first-interaction, edit count, revisit flag
- **Section-Level**: Mean pace, pause counts, back-navigation
- **Survey-Level**: Total duration, speed trajectory, time-of-day
- **Statistical**: Variance, IQR, entropy, skewness, kurtosis
- **Total**: 40 features across 4 categories

---

## Anomaly Detection

- **Definition**: Significant deviation in timing behavior
- **Methods**:
  - IQR-based thresholding (robust to non-normality)
  - Rule-based (e.g., zero back-navigation >20 questions)
- **Comparison**: IQR vs. Z-score (IQR preferred for skewed data)
- **Validation**: Synthetic datasets with injected anomalies

---

## Evaluation Methodology

- **Levels**: Feature validation (Mann-Whitney U) + Detection performance
- **Metrics**: Precision, Recall, F1-score (targets: 0.80/0.75)
- **Baselines**: Aggregate duration threshold, single-feature rule
- **Synthetic Data**: Log-normal/Poisson distributions for realism

---

## Project Timeline

| Phase | Weeks | Key Activities |
|-------|-------|----------------|
| Proposal | 1-2 | Writing, planning |
| Literature & Cataloguing | 3-7 | Review, features |
| Design | 8-9 | Architecture |
| Parsers | 10-13 | Implementation |
| Features | 14-18 | Extraction module |
| Detection | 19-21 | Anomaly logic |
| Midway | 22 | Review |
| Validation | 23-26 | Testing |
| Output | 27-29 | Docs |
| Report | 30-31 | Writing |
| Submission | 32 | Final |

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
- Thresholds may not generalize across contexts
- Preliminary taxonomy; some features may be non-discriminative
- No real-world validation against known anomalies
- Class imbalance in synthetic datasets

---

## Expected Outcomes

- Python feature library (30-50 features)
- Paradata format guide
- Synthetic validation dataset
- Validation report (precision/recall)
- 5,000-7,000 word report
- Structured output datasets

---

## AI-Assisted Development

- **Tools**: GitHub Copilot, Claude, ChatGPT
- **Tasks**: Code generation, proofreading, API clarification
- **Validation**: Line-by-line review, unit testing, documentation
- **Transparency**: AI Usage Log maintained

---

## Conclusion

- **Contribution**: Bridge between survey methodology and scalable implementation
- **Impact**: Enable data quality assessment using paradata at scale
- **Next Steps**: Implementation, validation, real-world application
- **Questions?**

---

## References

- Groves et al. (2009) - Survey Methodology
- Couper (1998) - CASIC quality
- Yan & Tourangeau (2008) - Response times
- Wenz et al. (2019) - Fabrication detection
- Kreuter (2013) - Paradata improvements
- And 9 others...

*End of Presentation*