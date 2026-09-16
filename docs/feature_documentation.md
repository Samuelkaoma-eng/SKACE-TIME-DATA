# Paradata Feature Documentation

**Project:** Automated Extraction and Analysis of Timing-Based Paradata Features for Survey Quality Assurance  
**Student:** Samuel Kaoma (2022016530) · **Course:** CSC 4004 · **Supervisor:** Mr. Mofya Phiri  
**Repository:** https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA  

This document describes the 40 timing and behavioral features extracted by the automated paradata pipeline, distributed across four granularities: Question, Section, Survey, and Statistical.

**Source status (revised September 2026).** Two sources previously cited in the last column, Wenz, Kreuter and Janke (2019) and Conrad, Tourangeau and Couper (2013), could not be located as cited and have been withdrawn; the features that relied on them are marked. The remaining sources exist, but the passage supporting each specific feature is still being confirmed. The final report's Appendix F is the authoritative feature-to-source map.

**Implementation notes.** S-09 matches only `back` and `backward` events, while V-05, V-06 and V-10 also match `jump`, the event name ODK uses. At interview level, S-04 averages to one by construction when sections have equal numbers of questions, and Q-01, T-06 and S-01 coincide under the same condition. Q-03 equals Q-08 minus one. Q-02 falls back to the duration of the first event when a log has no separate field start and end markers.

## 1. Question-Level Features (Q-Level)
*Extracted per specific survey field (question).*

| ID | Feature Name | Definition & Formula | Interpretation | Literature Source |
|---|---|---|---|---|
| **Q-01** | `response_time_ms` | Sum of `duration_ms` across the field's non-navigation events (active time on the field; gaps between visits are excluded). | Represents primary cognitive engagement time on a single item. | Yan & Tourangeau (2008) |
| **Q-02** | `time_to_first_interaction` | `duration_ms` of the first log event on the field. | Indicates initial reading and comprehension time before action. | Couper (1998) |
| **Q-03** | `edit_count` | `total_events - 1` | Identifies questions requiring repeated changes, indicating item difficulty. | Withdrawn; to be re-sourced (report Appendix F) |
| **Q-04** | `revisit_flag` | 1 if the field is revisited non-consecutively after the respondent has moved away, else 0. | Binary identifier for genuine non-linear traversal rather than simple multi-event editing. | Withdrawn; to be re-sourced (report Appendix F) |
| **Q-05** | `revisit_count` | Number of times the field is re-entered after leaving it. | Indicates significant respondent doubt or survey complexity. | Kreuter (2013) |
| **Q-06** | `field_completion_ratio` | 1.0 if `response_time_ms > 0` | Binary representation of data presence via timing logs. | Groves et al. (2009) |
| **Q-07** | `idle_time_ms` | Sum of inter-event gaps > 0 for a single field sequence. | Distraction or heavy cognitive load during answering. | Withdrawn; to be re-sourced (report Appendix F) |
| **Q-08** | `keystroke_count` | Total number of recorded paradata events for the node. | Proxy for response complexity (open-ended vs categorical). | Yan & Tourangeau (2008) |
| **Q-09** | `constraint_trigger_count` | Number of events containing 'error', 'invalid', 'constraint'. | Frustration indicators and poor survey validation design. | Couper (1998) |
| **Q-10** | `first_to_last_interaction_duration` | `max(end_ms) - min(start_ms)` for a field. | Total temporal footprint of the question including internal pauses. | Withdrawn; to be re-sourced (report Appendix F) |

## 2. Section-Level Features (S-Level)
*Extracted over logical groupings of questions (sections/modules).*

| ID | Feature Name | Definition & Formula | Interpretation | Literature Source |
|---|---|---|---|---|
| **S-01** | `mean_section_pace` | Mean `Q-01_response_time_ms` within the section. | Identifies if certain modules induce fatigue. | Kreuter (2013) |
| **S-02** | `section_duration_ms` | Sum of `duration_ms` for all events in the section. | Total time investment for a specific topical module. | Groves et al. (2009) |
| **S-03** | `within_section_variance` | Variance of `Q-01` values within the section. | High variance indicates natural varied cognitive load; low indicates speeding. | Withdrawn; to be re-sourced (report Appendix F) |
| **S-04** | `section_to_section_pace_ratio` | `S-01 / Global Mean Pace` | Identifies specifically unnatural rapid-answering in sensitive modules. | Withdrawn; to be re-sourced (report Appendix F) |
| **S-05** | `pause_count_5s` | Count of gaps > 5,000ms. | Catching minor distractions or reading heavy text blocks. | Yan & Tourangeau (2008) |
| **S-06** | `pause_count_30s` | Count of gaps > 30,000ms. | Catching major interruptions or enumerator breaks. | Kreuter (2013) |
| **S-07** | `mean_pause_duration_ms` | Mean of all gap durations. | Quantifies typical distraction length. | Withdrawn; to be re-sourced (report Appendix F) |
| **S-08** | `max_pause_duration_ms` | Maximum gap duration. | Pinpoints the single largest disruption in the section. | Withdrawn; to be re-sourced (report Appendix F) |
| **S-09** | `back_nav_count_section` | Count of 'backward' events. | Module complexity or confusion. | Couper (1998) |
| **S-10** | `section_completion_rate` | Questions interacted / Total Questions. | Dropout mapping within surveys. | Groves et al. (2009) |

## 3. Survey-Level Features (V-Level)
*Extracted over the complete interview session.*

| ID | Feature Name | Definition & Formula | Interpretation | Literature Source |
|---|---|---|---|---|
| **V-01** | `total_interview_duration_ms` | `max(end) - min(start)` | The primary macro-indicator of speeding or fabrication. | Yan & Tourangeau (2008) |
| **V-02** | `speed_trajectory_early` | Pace of first 33% of events. | Baseline rhythm before fatigue. | Kreuter (2013) |
| **V-03** | `speed_trajectory_late` | Pace of final 33% of events. | Usually faster due to satisficing and fatigue. | Withdrawn; to be re-sourced (report Appendix F) |
| **V-04** | `speed_trajectory_ratio` | `V-03 / V-02` | Ratios far below 1.0 indicate severe satisficing (rushing the end). | Withdrawn; to be re-sourced (report Appendix F) |
| **V-05** | `back_navigation_rate` | Back events / total events. | Global interview difficulty or poor navigation flow. | Couper (1998) |
| **V-06** | `back_navigation_total_count` | Sum of back events. | Absolute count of respondent course-corrections. | Groves et al. (2009) |
| **V-07** | `time_of_day_hour` | Hour derived from `min(start)`. | Fabrication detection (e.g., surveys logged at 2:00 AM). | Withdrawn; to be re-sourced (report Appendix F) |
| **V-08** | `day_of_week` | Day derived from `min(start)`. | Helps track expected working hours vs weekend anomalies. | Kreuter (2013) |
| **V-09** | `session_length_vs_median` | `V-01 / median(V-01_all)` | Relative speed compared to the sample population. | Yan & Tourangeau (2008) |
| **V-10** | `zero_back_nav_flag` | 1 if the interview contains at least 20 consecutive non-back-navigation events. | Flags unnaturally linear progression even if a rare early back-navigation event exists elsewhere in the interview. | Withdrawn; to be re-sourced (report Appendix F) |

## 4. Statistical Features (T-Level)
*Extracted by summarizing the distribution of Question-Level response times (Q-01).*

| ID | Feature Name | Definition & Formula | Interpretation | Literature Source |
|---|---|---|---|---|
| **T-01** | `rt_variance` | Variance of `Q-01`. | Low variance = robotic answering; High variance = natural. | Withdrawn; to be re-sourced (report Appendix F) |
| **T-02** | `rt_iqr` | 75th percentile - 25th percentile. | Robust spread metric insensitive to massive outliers. | Kreuter (2013) |
| **T-03** | `rt_entropy` | Shannon Entropy over normalized RT distribution. | Low entropy indicates highly clustered, uniform timing (fabrication). | Withdrawn; to be re-sourced (report Appendix F) |
| **T-04** | `rt_skewness` | Fisher-Pearson coefficient of skewness. | Natural surveys are right-skewed. Left-skew indicates anomaly. | Yan & Tourangeau (2008) |
| **T-05** | `rt_kurtosis` | Excess kurtosis. | Leptokurtic (high kurtosis) means answering is heavily clustered. | Withdrawn; to be re-sourced (report Appendix F) |
| **T-06** | `rt_mean` | Average `Q-01`. | Basic central tendency comparison. | Groves et al. (2009) |
| **T-07** | `rt_median` | Median `Q-01`. | Central tendency robust to long reading times. | Yan & Tourangeau (2008) |
| **T-08** | `rt_cv` | Coefficient of Variation (Std / Mean). | Scale-invariant measure of timing uniformity. | Withdrawn; to be re-sourced (report Appendix F) |
| **T-09** | `rt_min` | Minimum `Q-01`. | Absolute fastest response limit (flags impossible speeds). | Couper (1998) |
| **T-10** | `rt_max` | Maximum `Q-01`. | Usually represents the largest distraction. | Withdrawn; to be re-sourced (report Appendix F) |
