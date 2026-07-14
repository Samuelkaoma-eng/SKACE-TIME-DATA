# SKACE-Time-Data: Feature Library Documentation

**Project:** Automated Extraction and Analysis of Timing-Based Paradata Features for Survey Quality Assurance  
**Student:** Samuel Kaoma (2022016530) · **Course:** CSC 4004 · **Supervisor:** Mr. Mofya Phiri  
**Repository:** https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA  

This document serves as the formal guide for the Python feature extraction library built for the seed project. The library converts Common Intermediate Representation (CIR) parsed logs into 40 distinct paradata features aligned with the theories of Groves, Conrad, and Kreuter.

---

## 1. Feature Categories

The library systematically aggregates data across 4 distinct hierarchical levels:
*   **V-Series (Survey Level):** Global metrics spanning the entire survey duration.
*   **S-Series (Section Level):** Module-specific metrics tracking respondent progression and fatigue within conceptual groups.
*   **Q-Series (Question Level):** Granular interaction metrics at the specific node level (edit counts, idle times).
*   **T-Series (Statistical/Timing Level):** Global mathematical variance and entropy measures reflecting timing distribution.

---

## 2. Feature Definitions (30-50 Implementation)

Below are the 40 explicitly tracked parameters outputted by the pipeline:

### V-Series (Global/Survey)
1.  `V-01_total_interview_duration_ms`: Total gross time from first to final interaction.
2.  `V-02_speed_trajectory_early`: Mean pace across the first third of events.
3.  `V-03_speed_trajectory_late`: Mean pace across the final third of events.
4.  `V-04_speed_trajectory_ratio`: `V-03 / V-02` (fatigue or speeding indicator).
5.  `V-05_back_navigation_rate`: `%` of interactions that were backwards movement.
6.  `V-06_back_navigation_total_count`: Absolute back-navigations.
7.  `V-07_time_of_day_hour`: Starting hour (0-23).
8.  `V-08_day_of_week`: Starting day (0-6).
9.  `V-09_session_length_vs_median`: Ratio against population median.
10. `V-10_zero_back_nav_flag`: Identifies absolute lack of correction (straight-lining).

### T-Series (Statistical/Timing)
11. `T-01_rt_variance`: Absolute variance of question response times (RTs).
12. `T-02_rt_iqr`: Interquartile Range covering 25th-75th percentiles of RT.
13. `T-03_rt_entropy`: Shannon entropy index measuring randomness of timings.
14. `T-04_rt_skewness`: Mathematical skew of the RT distribution.
15. `T-05_rt_kurtosis`: Tailedness of RTs.
16. `T-06_rt_mean`: Average RT.
17. `T-07_rt_median`: 50th percentile RT.
18. `T-08_rt_cv`: Coefficient of Variation (`Standard Deviation / Mean`).
19. `T-09_rt_min`: Fastest interaction natively logged.
20. `T-10_rt_max`: Slowest discrete interaction logged.

### S-Series (Section Level)
21. `S-01_mean_section_pace`: Weighted pace per section group.
22. `S-02_section_duration_ms`: Cumulative section duration.
23. `S-03_within_section_variance`: Distribution of RTs inside a section grouping.
24. `S-04_section_to_section_pace_ratio`: Progression speeding gradient.
25. `S-05_pause_count_5s`: Iterations where respondent idles > 5 seconds.
26. `S-06_pause_count_30s`: Iterations where respondent idles > 30 seconds.
27. `S-07_mean_pause_duration_ms`: Average length of identified pauses.
28. `S-08_max_pause_duration_ms`: Absolute longest pause event.
29. `S-09_back_nav_count_section`: Module-isolated corrections.
30. `S-10_section_completion_rate`: Progress vector representing early abandonment.

### Q-Series (Question Level)
31. `Q-01_response_time_ms`: Sum of event durations on the field (active interaction time, excluding navigation events and gaps between visits).
32. `Q-02_time_to_first_interaction`: Latency from node load to initial user tap.
33. `Q-03_edit_count`: Number of recorded events on the field beyond the first, treated as edits within the visit.
34. `Q-04_revisit_flag`: Boolean identifying returning to a previously submitted question.
35. `Q-05_revisit_count`: Count of discrete return events.
36. `Q-06_field_completion_ratio`: Binary per field: 1.0 when the field recorded active time, 0.0 otherwise (a timing-based proxy, since answer content is not logged).
37. `Q-07_idle_time_ms`: Explicit math for periods with no input mutation.
38. `Q-08_keystroke_count`: Number of paradata events recorded on the field, used as a proxy because neither platform logs individual keystrokes.
39. `Q-09_constraint_trigger_count`: Invalid inputs logged prior to completion.
40. `Q-10_first_to_last_interaction_duration`: Span from the first to the last event on the field, including internal gaps.

---

## 3. Usage Examples

Implementing the feature extractor on parsed CIR data:

```python
import pandas as pd
from src.features.survey_features import SurveyFeatureExtractor
from src.features.statistical_features import StatisticalFeatureExtractor

# Sample CIR Structured Data
cir_data = pd.DataFrame([{
    'start_ms': 10000, 
    'end_ms': 12000, 
    'duration_ms': 2000,
    'event_type': 'question'
}])

# Extract V-Series Attributes
survey_extractor = SurveyFeatureExtractor()
v_features = survey_extractor.extract(cir_data)
print(f"Total Session Duration: {v_features['V-01_total_interview_duration_ms']}")

# Extract T-Series (Entropy/CV)
stat_extractor = StatisticalFeatureExtractor()
t_features = stat_extractor.extract(cir_data)
print(f"Shannon Entropy Timing Map: {t_features['T-03_rt_entropy']}")
```
