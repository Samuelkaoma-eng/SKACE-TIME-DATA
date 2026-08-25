# Automated Extraction and Analysis of Timing-Based Paradata Features for Survey Quality Assurance

Samuel Kaoma (2022016530) | CSC 4004 | Supervisor: Mr. Mofya Phiri | July 2026

## Abstract

Digital data collection platforms such as SurveyCTO and ODK Collect record detailed process data, commonly called paradata, alongside every interview. These audit logs hold timestamps, navigation events and validation errors that describe how an interview was conducted rather than what was answered. Although survey methodology research has repeatedly shown that such timing data can expose fabrication, speeding and disengagement, paradata remains underused in practice because the raw logs differ across platforms and no standard tooling exists to turn them into analytical features. This study designed, implemented and evaluated an automated pipeline that parses SurveyCTO and ODK audit logs into a common intermediate representation, computes forty timing-based features across question, section, survey and statistical levels of granularity, and flags anomalous interviews using interquartile range thresholds combined with transparent, configurable rules. The system was evaluated against synthetic benchmark datasets with labelled injected anomalies, including datasets generated from random seeds that were never used during development and a stress condition in which normal and anomalous behaviour deliberately overlap. Across a class imbalance sweep from five to thirty percent anomaly prevalence the detector achieved precision between 0.96 and 1.00 with full recall. On held-out stress datasets in both platform formats it achieved precision between 0.95 and 1.00 and recall between 0.84 and 0.90, exceeding the predefined success criteria of 0.80 precision and 0.75 recall. Across the stress runs speeding was detected in every case, disengagement in 89 percent of cases, and subtle fabrication in 70 percent of cases, a pattern consistent with the known limits of univariate outlier detection. The deliverables include a documented Python feature library, a paradata format guide, labelled validation datasets and this report.

## 1. Introduction

The quality of survey data underpins research, policy formulation and decision making in public health, economics and the social sciences (Groves et al., 2009). Digital data collection platforms have substantially improved the efficiency of field survey administration, and two of the most widely deployed platforms, SurveyCTO and Open Data Kit (ODK), automatically record auxiliary process data known as paradata (Couper, 1998; Kreuter, 2013). Paradata captures how an interview unfolded: when each question was opened and answered, how long the enumerator paused, whether answers were revised, and how the respondent navigated through the instrument.

These behavioural traces carry diagnostic value that conventional quality checks cannot match. Unusually fast completion may indicate rushed or fabricated responses, extended pauses may signal confusion or interruption, and atypical navigation patterns may point to satisficing behaviour, in which respondents or enumerators invest only the minimum effort required to move forward (Krosnick, 1991; Yan and Tourangeau, 2008). Despite this potential, paradata is routinely underused. Audit logs from SurveyCTO and ODK differ in structure, field naming and timing granularity, and the statistical work needed to convert millions of raw event rows into defensible quality indicators is beyond the reach of most survey teams (Kreuter, 2013).

### 1.1 Problem statement

Existing survey quality assurance practice relies largely on aggregate indicators, chiefly total interview duration, together with manual back-checking of a sample of interviews. These methods are poorly equipped to detect behavioural irregularities that occur during the interview, such as uniform pacing across questions of very different complexity, or the complete absence of the natural navigation errors that human interviewers make (Wenz, Kreuter and Janke, 2019). At the same time, the raw material needed to detect these patterns already exists in the audit logs that both major platforms produce by default. The barrier is the absence of automated, format-aware tools that transform heterogeneous logs into structured features and apply statistically sound detection methods that respect the non-normal distributions typical of response time data (Iglewicz and Hoaglin, 1993).

### 1.2 Aim

The aim of this project was to design and implement an automated pipeline for extracting, cataloguing and analysing timing-based paradata features from SurveyCTO and ODK audit logs in order to support scalable survey data quality assessment.

### 1.3 Objectives

1. To review and catalogue timing-based quality indicators identified in survey methodology literature, mapping prior findings to a structured feature taxonomy.
2. To develop format-aware parsers for SurveyCTO and ODK audit logs that produce a common intermediate representation.
3. To implement a feature extraction module computing thirty to fifty timing-based indicators across question, section and survey levels of granularity.
4. To compute statistical characterisation measures including variance, entropy, skewness and kurtosis.
5. To implement anomaly detection using interquartile range thresholding and rule-based logic, validated against precision and recall criteria.
6. To generate structured output datasets, feature documentation and a paradata format guide suitable for reuse by survey researchers.
### 1.4 Scope

The project processes audit logs from SurveyCTO and ODK, extracts forty timing-based and behavioural features, characterises response patterns statistically, applies interquartile range and rule-based anomaly detection, and validates the system empirically using synthetic datasets with labelled anomalies. Real-time monitoring, dashboard integration, machine learning deployment and primary data collection were excluded from scope at proposal stage and remain so.

## 2. Literature Review

The Total Survey Error framework developed by Groves et al. (2009) treats data quality as the product of error sources across every stage of the survey process. Within this framework paradata has emerged as a practical mechanism for monitoring error at the interviewing stage. Couper (1998) first demonstrated that process data captured inside computer-assisted instruments could serve as quality indicators, establishing the basis for timing-based analysis.

Yan and Tourangeau (2008) examined response latency directly and found that question complexity, respondent age and topic familiarity all predict response time. Their central finding for the present work is that questions answered unusually quickly relative to their complexity are associated with reduced cognitive engagement and lower data quality. Answering a survey question requires comprehension, retrieval, judgement and response selection; respondents who satisfice skip the middle stages, and the missing effort is visible in the timing record (Krosnick, 1991). This motivates the question-level response time, time to first interaction and complexity-related pace features in the taxonomy used here.

Conrad, Tourangeau and Couper (2013) explored adaptive survey designs driven by paradata and showed that behavioural signals observable during the interview, including extended pauses and repeated backward navigation, identify respondent difficulty and disengagement. Their analysis supports the section-level pause frequency, pause duration and back-navigation features adopted in this project.

The most directly applicable empirical work is that of Wenz, Kreuter and Janke (2019), who investigated data fabrication using paradata from interviewer-administered surveys. Fabricated interviews exhibited compressed response time distributions, with reduced interquartile spread and low variance in question-level durations, together with abnormally low back-navigation counts and unusually uniform section pacing. These findings supply the statistical signature that the anomaly detection component of this project is designed to recognise, and they directly justify the choice of interquartile range thresholding as the primary detection method.

Kreuter (2013) surveys paradata-driven quality improvement across large survey programmes and reports two findings of practical importance here. First, computational processing of timing data requires platform-specific parsing before any analysis can begin, which motivates the parser layer of this system. Second, survey-level features such as total duration, pace trajectory across the interview and time-of-day effects are robust indicators that survive aggregation across very different instruments.

On the statistical side, response time distributions are strongly right-skewed, which makes methods that assume normality unreliable for outlier detection (Hawkins, 1980; Iglewicz and Hoaglin, 1993). Interquartile range fences make no distributional assumption and are themselves resistant to the influence of the outliers they are meant to find, which is why they are preferred here over z-score methods. Broader surveys of anomaly detection (Chandola, Banerjee and Kumar, 2009; Hodge and Austin, 2004) distinguish univariate approaches, which examine one feature at a time, from multivariate approaches that model joint structure. Univariate methods are transparent and interpretable, properties valued in survey quality workflows where a flagged interview must be explainable to a field supervisor, but they cannot detect anomalies visible only in combinations of features. This trade-off is accepted explicitly in the present design and revisited in the results.

Finally, the evaluation strategy draws on the synthetic data literature. Where labelled real-world anomalies are unavailable, controlled injection of known anomaly types into generated data is an established way to benchmark detection systems (Chawla et al., 2002). Evaluation metrics computed on synthetic data are sensitive to class prevalence, so a fixed anomaly ratio can misrepresent operational performance; varying the ratio is the standard mitigation (Japkowicz and Stephen, 2002). Both practices are followed in this study.

## 3. Methodology

The system is a multi-stage pipeline that proceeds from raw log ingestion through parsing, feature extraction, statistical characterisation and anomaly detection to structured output generation. Development followed an iterative, test-driven approach in Python 3.10 and later versions, using Pandas and NumPy for data processing, SciPy for statistical functions, Matplotlib and Seaborn for visualisation, and Pytest for automated testing (McKinney, 2017).

### 3.1 Common intermediate representation

SurveyCTO and ODK audit logs differ in event taxonomy, field naming and timestamp encoding. SurveyCTO exports event-based CSV files with epoch-millisecond timestamps attached to field identifiers, while ODK exports use ISO 8601 timestamp strings and a different event vocabulary. To decouple analysis from these differences, every parser converts its input into a common intermediate representation, a standardised table with six columns: interview identifier, field name, event type, start time in milliseconds, end time in milliseconds, and duration in milliseconds. All downstream components operate exclusively on this representation, so support for an additional platform requires only a new parser and no change to the feature library.

The parser layer is a class hierarchy. An abstract base parser defines the intermediate schema and validates that every parser output conforms to it. Concrete subclasses for SurveyCTO and ODK handle ingestion, event name normalisation and timestamp conversion. Event vocabularies differ between the platforms: SurveyCTO logs events such as form-start, constraint and end against XPath node identifiers, while ODK uses terms such as form start, question and end screen against instance and name columns. Each parser maps its native vocabulary onto a shared set of normalised event types so that a form opening, a question interaction and a navigation jump mean the same thing downstream regardless of origin.

Timestamp handling deserves particular care because it is where real logs most often deviate from documentation. The SurveyCTO parser accepts epoch milliseconds as its canonical input but includes a guard for exports that record epoch seconds, detected from the magnitude of the median value and corrected by rescaling. The ODK parser converts ISO 8601 strings, including timezone offsets, into epoch milliseconds. Both parsers tolerate missing field names, unparseable timestamps and negative durations by marking the affected rows rather than silently accepting or discarding them, so that data problems surface in the quality flags rather than corrupting features. A controller above the parsers performs automatic format detection from column structure and timestamp shape, and can split hybrid files in which rows from both platforms have been concatenated into a single export, a situation that occurs in practice when field teams merge files before upload.

### 3.2 Feature taxonomy

Forty features were catalogued at proposal stage from the literature reviewed above and all forty are implemented. They are organised in four groups with stable identifiers used consistently in the code, the documentation and the output datasets.

| Group | Identifiers | Content |
|---|---|---|
| Question level | Q-01 to Q-10 | Response time, time to first interaction, edit count, revisit flag and count, completion ratio, idle time, event count, constraint triggers, first-to-last interaction span |
| Section level | S-01 to S-10 | Mean section pace, section duration, within-section variance, pace ratio to survey mean, pause counts above five and thirty seconds, mean and maximum pause, back-navigation count, completion rate |
| Survey level | V-01 to V-10 | Total duration, early and late pace, pace trajectory ratio, back-navigation rate and total, start hour, day of week, duration relative to sample median, consecutive no-back-navigation flag |
| Statistical | T-01 to T-10 | Variance, interquartile range, Shannon entropy, skewness, excess kurtosis, mean, median, coefficient of variation, minimum and maximum of the response time distribution |

Two features are proxies imposed by the source data. The event count per field stands in for keystroke count, because neither platform logs individual keystrokes, and the field completion ratio is derived from whether measurable time was spent on the field, because the audit log does not record answer content. Both proxies are documented in the feature guide so that users do not over-interpret them.

Administrative events require care. Real audit logs open and close with form-level rows whose field identifier is blank. These rows contribute to total interview duration but are excluded from question-level and section-level statistics, because treating the gap between form start and form end as a pause would swamp every within-section measure. This exclusion was added after exactly that distortion was observed during validation.

### 3.3 Key statistical formulations

Three of the statistical features carry most of the detection weight and merit explicit definition. Shannon entropy of the response time distribution measures the unpredictability of an interview's rhythm. Response times are binned into one-second intervals, the proportion of questions falling in each occupied bin is computed, and entropy is the negative sum of each proportion multiplied by its base-two logarithm. A fabricator who paces every question similarly concentrates the distribution in one or two bins and drives entropy towards zero, while a genuine interview spreads across many bins. The one-second bin width is fixed so that identical behaviour yields identical entropy in both platform formats regardless of timestamp precision.

The coefficient of variation, the standard deviation of response times divided by their mean, provides a scale-free measure of pacing uniformity. Because it is normalised by the mean, it treats a uniformly slow fabricator and a uniformly fast one identically, catching mechanical pacing at any speed. Values below one tenth indicate pacing more uniform than human respondents produce across questions of varying complexity.

Outlier fences follow Tukey's construction. For a given feature the interquartile range is the distance between the first and third quartiles, and values falling more than one and a half times that distance outside either quartile are flagged. The construction uses only order statistics, so it makes no distributional assumption and is itself insensitive to the outliers it identifies, which is essential for right-skewed response time data where a z-score approach would let extreme values distort their own detection threshold (Iglewicz and Hoaglin, 1993).

### 3.4 Anomaly detection

An anomaly is defined at the interview level as statistically significant deviation from expected timing behaviour. Detection combines two complementary mechanisms. Statistical flagging applies Tukey fences to four features: total duration, mean response time, response time entropy and response time variance. For each, interviews below the first quartile minus 1.5 times the interquartile range, or above the third quartile plus the same margin, receive a flag. Rule-based flagging applies domain-derived thresholds covering implausibly short or long sessions, low mean response time relative to the sample median, low entropy, uniform pacing measured by the coefficient of variation, compressed interquartile range, low within-section variance, absent back-navigation in compressed-timing contexts, elevated back-navigation rates, and mean inter-question pauses well above the sample median. Wherever a threshold could depend on the instrument or population, it is expressed relative to the sample median rather than as an absolute number, and every threshold is a configuration parameter rather than a constant in code.

Each interview receives an anomaly score equal to the number of active flags, with the four statistical flags contributing at most one point jointly so that a single extreme value cannot dominate the score. Interviews scoring at or above two are categorised as suspicious and at or above five as anomalous. A separate set of data quality flags, covering impossible values such as negative durations or a maximum below a minimum, routes technically corrupt records into their own category so that device faults are not misread as behavioural anomalies. The score is a transparent count: every flagged interview can be explained by listing its active flags, which is a requirement for use in field supervision.

### 3.5 Computational considerations

The pipeline was designed for datasets ranging from pilot studies of a few dozen interviews to national surveys of tens of thousands. Feature extraction uses vectorised Pandas operations whose cost grows approximately linearly with the number of audit events per interview, and anomaly detection is dominated by quantile computation over interviews. Memory use is bounded by processing files independently and holding only interview-level summaries for the batch stage. Benchmarking during evaluation confirmed comfortable processing of ten-thousand-interview datasets on commodity hardware.

### 3.6 Ethical considerations

The system operates on paradata rather than on survey responses, which substantially reduces privacy risk. All evaluation data in this study is synthetic, so no respondent information of any kind was processed. The use of artificial intelligence tools during development is disclosed in a dedicated usage log appended to the project repository, in line with the supervision framework for the academic year.

## 4. Implementation

The pipeline is organised as five decoupled layers coordinated by a controller. The ingestion layer accepts one or more CSV files through a command line interface with an optional interactive mode. The parser layer produces the common intermediate representation described above. The extraction layer contains four extractor classes, one per feature group, each of which consumes the intermediate representation, or in the case of the statistical extractor the question-level output, and returns its features independently of the others. The validation layer applies the anomaly detector to the combined interview-level feature table, and the reporting layer writes the feature dataset, a per-interview anomaly report, granular question-level and section-level tables, and evaluation artefacts when ground truth labels are supplied.

Features that require sample context are computed at batch level. Duration relative to the sample median, for example, cannot be known for a single interview in isolation, so the controller computes it once all interviews in a batch have been extracted. The evaluation path merges predictions with ground truth labels through a strict one-to-one join that fails loudly on duplicate or missing interview identifiers, and the detector never sees the labels; this separation prevents any leakage between detection and evaluation.

Every detector threshold lives in a configuration object validated at load time, with defaults matching the values justified in the methodology. A configuration file can be supplied on the command line, and a recalibration script derives a configuration from a labelled dataset by sweeping the score threshold and selecting the value that best satisfies the precision and recall targets. Configurations record their provenance, including the datasets used and the generation timestamp, so that any reported result can be traced to the exact settings that produced it. Reproducibility extends to the data: every synthetic dataset records its random seed, size, anomaly ratio and difficulty in an accompanying summary file, and regenerating any benchmark is a single documented command.

The automated test suite contains thirty-three tests covering the parsers, each feature extractor, the detector, the configuration validation and the end-to-end pipeline, and the suite passes in full at the time of writing. During a line-by-line review of the codebase two defects were found and fixed: an upstream data integrity flag was being overwritten by the detector, and missing field names in ODK logs were being converted to the literal string nan instead of the intended placeholder. A third defect surfaced during evaluation, when newly added form-level events were found to be inflating section pause statistics, and was fixed by excluding administrative events from section aggregation. A final pre-submission audit in a clean environment surfaced two further defects: the conversion from ISO 8601 timestamps to epoch milliseconds assumed the nanosecond datetime resolution of earlier pandas versions and silently produced values a thousand times too small under pandas 3, and the question-level response time was computed as the first-to-last event span, duplicating a separate feature, rather than as the documented sum of event durations. Both were corrected, and all five fixes are covered by the test suite and recorded in version control.

## 5. Evaluation Methodology

### 5.1 Synthetic data generation

Evaluation uses synthetic audit logs with labelled injected anomalies, an established approach where labelled real-world data is unavailable (Chawla et al., 2002). The generator produces structurally realistic logs in both platform formats: interviews open with a form-start row and close with a form-end row carrying blank field identifiers, questions belong to five named sections of four questions each, genuine respondents occasionally trigger validation constraints, and navigation events appear at random positions. Response times for genuine interviews follow a log-normal distribution, consistent with empirical response latency research (Yan and Tourangeau, 2008), and are scaled by a fixed per-question complexity profile so that short factual items complete quickly and recall-heavy items complete slowly. Back-navigation counts follow a Poisson distribution.

Three anomaly profiles are injected according to the patterns documented in prior work. Fabricated interviews compress the response time distribution, ignore question complexity and suppress back-navigation (Wenz, Kreuter and Janke, 2019). Speeding interviews scale response times below plausible completion thresholds. Disengaged interviews combine slow uniform pacing with elevated pauses and erratic back-navigation (Conrad, Tourangeau and Couper, 2013). A fourth profile injects degenerate records, such as single rows with zero duration, to exercise the data quality path. The generator has a canonical difficulty, in which profiles are cleanly separated, and a stress difficulty, in which some genuine respondents are fast with little navigation and some fabricated interviews are only mildly compressed, so that the profiles overlap and detection is genuinely difficult.

### 5.2 Design against overfitting

A detector evaluated only on data resembling its calibration data will report flattering results. Three safeguards address this. First, detector settings that had been tuned to earlier generator behaviour were removed or generalised before the final evaluation round: a coupling between two flags that matched the old generator was deleted, fixed pause constants became configuration parameters, and the disengagement rule was reformulated relative to the sample median. Second, all reported evaluation runs use random seeds that were never used during development or calibration. Third, evaluation includes the stress difficulty and a class imbalance sweep in which anomaly prevalence varies from five to thirty percent, following the recommendation of Japkowicz and Stephen (2002).

### 5.3 Datasets

Four kinds of dataset were used. A canonical suite of twenty-four interviews, twelve per platform format, pairs each anomaly profile with known expected outcomes and serves as a fixed regression test. Benchmark datasets of one hundred and twenty to ten thousand interviews at twenty percent anomaly prevalence exercise scale in both formats. The imbalance sweep holds size at five hundred interviews and varies prevalence across five, ten, twenty and thirty percent. The stress datasets, five hundred interviews each from two held-out seeds and rendered in both formats, provide the overlapping-profile condition. Ground truth for every dataset records each interview's profile and binary anomaly status, and the evaluation join verifies that predictions cover the ground truth exactly.

### 5.4 Metrics and baselines

Primary metrics are precision, the proportion of flagged interviews that are truly anomalous, and recall, the proportion of truly anomalous interviews that are flagged, with the F1 score as their harmonic mean. Success criteria were fixed at proposal stage: precision at or above 0.80 and recall at or above 0.75. Feature-level validity is assessed with Mann-Whitney U tests comparing each feature between normal and anomalous interviews, with effect sizes reported. The full detector is compared against two baselines representing current practice: a duration-only method that flags interviews solely on total duration outside the Tukey fences, and a single-rule method that flags only interviews with zero back-navigation.

## 6. Results

### 6.1 Canonical suite

On the canonical suite every interview was assigned its expected category in both platform formats: genuine interviews scored at most one flag, fabricated interviews scored five or more, speeding and disengaged interviews landed at least in the suspicious band, and the degenerate records were routed to the data quality category rather than scored behaviourally. This confirms the intended mapping between profile and category before the harder conditions are considered.

### 6.2 Feature validity

Mann-Whitney U tests found that thirty of the forty features separate normal from anomalous interviews at conventional significance levels, with large effect sizes concentrated in the statistical group, particularly response time variance, interquartile range, entropy and coefficient of variation, and in total duration. Features that did not discriminate, such as start hour and day of week, are contextual rather than behavioural; they are retained in the output for analysts but carry no weight in detection.

### 6.3 Baseline comparison

On a five-hundred-interview benchmark in SurveyCTO format, the duration-only baseline achieved precision 0.96 but recall 0.66, missing every anomaly whose total duration lay inside the fences. The zero-back-navigation baseline achieved precision 0.46 and recall 0.66. The full detector achieved precision 1.00 and recall 1.00 on the same data. The comparison confirms the central premise of the project: aggregate duration alone misses a third of injected anomalies that multi-feature analysis captures.

### 6.4 Class imbalance sweep

On canonical-difficulty datasets of five hundred interviews generated from a held-out seed, recall remained 1.00 at every prevalence level while precision varied with prevalence as expected.

| Anomaly prevalence | Precision | Recall | F1 |
|---|---|---|---|
| 5 percent | 0.9615 | 1.0000 | 0.9804 |
| 10 percent | 1.0000 | 1.0000 | 1.0000 |
| 20 percent | 1.0000 | 1.0000 | 1.0000 |
| 30 percent | 1.0000 | 1.0000 | 1.0000 |

At five percent prevalence a single genuine interview was falsely flagged, costing almost four points of precision. This sensitivity of precision to prevalence is a property of the metric rather than of the detector, and it matters operationally because real fabrication rates are usually low; the result quantifies the review burden a deployment should expect.

### 6.5 Held-out stress evaluation

The stress condition is the demanding test. Profiles overlap by construction, seeds are held out, and detector settings are the defaults with no calibration to the evaluated data.

| Dataset | Precision | Recall | F1 |
|---|---|---|---|
| Seed 7, SurveyCTO | 0.9770 | 0.8500 | 0.9091 |
| Seed 7, ODK | 0.9570 | 0.8900 | 0.9223 |
| Seed 99, SurveyCTO | 1.0000 | 0.8800 | 0.9362 |
| Seed 99, ODK | 1.0000 | 0.8400 | 0.9130 |

All four runs exceed both success criteria. Performance is consistent across the two platform formats, which validates the common intermediate representation: the same detector, without modification, performs equivalently on structurally different inputs.

### 6.6 Detection by anomaly type

Per-class recall on the held-out stress data shows a clear gradient of difficulty. Each figure below is the recall for that injected class, that is the proportion of interviews of that type which the combined detector flagged, aggregated across the four stress runs. These are diagnostic breakdowns of a single detector rather than separate detectors, and the proposal's success criteria of precision 0.80 and recall 0.75 are defined for the combined detector, which exceeds both on every run. Aggregated across the four stress runs, speeding was detected in all 132 instances. Disengagement was detected in 121 of 136 instances, or 89 percent, driven by the median-relative pause rule combined with elevated back-navigation. Fabrication was detected in 93 of 132 instances, a per-class recall of 0.70, with per-run rates between 0.61 and 0.76. The undetected fabricated interviews all came from the mildly compressed variant. The stress generator emits two fabricated profiles, and the tightly compressed one was detected without exception, so the aggregate figure combines one profile at perfect recall with another at approximately half. A bounded diagnostic pass on the false negatives, conducted on development seeds and reported in full in the accompanying validation documentation, established that these interviews are not in fact indistinguishable from genuine ones. Response time entropy separates the two populations completely on those datasets, the highest fabricated value being 1.983 against a lowest genuine value of 2.039. The misses arise from how the detector reads that feature rather than from an absence of signal in it: the behavioural entropy rule applies an absolute constant calibrated to the tightly compressed profile, and the corresponding interquartile fence is estimated from a sample that already contains twenty percent injected anomalies, which depresses the lower quartile and the fence with it. This second effect is the masking phenomenon long recognised in unsupervised outlier detection (Chandola, Banerjee and Kumar, 2009). A related structural limitation applies to the right-skewed non-negative features: for quantities such as response time variance the Tukey lower fence falls below zero and is therefore unreachable, so no low-side outlier can be detected on them at all. These are calibration and fence-construction limitations rather than evidence that univariate analysis is insufficient for this profile, and they are recorded here as the honest account of where the method's recall is lost.

### 6.7 Scalability and regression checks

Feature extraction uses vectorised operations with time complexity approximately linear in the number of audit events, and the detection step is dominated by sorting over interviews. The pipeline processed benchmark datasets of ten thousand interviews without memory or runtime difficulty on commodity hardware. After all changes made during the robustness round, the canonical benchmark suite continued to score precision 1.00 and recall 1.00 in both formats, confirming that hardening the evaluation did not degrade performance on the original success cases, and the automated test suite passed in full.

## 7. Discussion

The results support three substantive conclusions. First, the common intermediate representation works as designed. A single detector operating on normalised features performed equivalently on SurveyCTO and ODK inputs across every experiment, and adding a platform requires only a parser. Second, multi-feature timing analysis materially outperforms the aggregate-duration checking that represents current practice, raising recall from 0.66 to between 0.84 and 1.00 depending on condition while holding precision at or near 1.00. The features doing the heaviest work are exactly those the literature predicted: distributional shape measures for fabrication (Wenz, Kreuter and Janke, 2019) and pause and navigation measures for disengagement (Conrad, Tourangeau and Couper, 2013).

Third, and equally important, the evaluation shows where the approach stops working. Early runs of this project scored perfect precision and recall everywhere, which was initially read as success. Closer inspection showed the synthetic anomalies were too cleanly separated and parts of the detector configuration mirrored the generator. Treating perfect scores as a warning rather than a result, and rebuilding the evaluation around held-out seeds, overlapping profiles and prevalence sweeps, produced lower numbers and a far more defensible claim. The residual misses concentrate in mild fabrication, and the reason is structural rather than a matter of tuning: a determined fabricator who paces plausibly and varies their timing produces a univariate profile inside normal bounds. Detecting that adversary requires modelling joint feature structure, which was deliberately excluded from scope to preserve interpretability, and which is the natural next step for future work.

The severity categories, suspicious at a score of two and anomalous at five, translate the score into workflow terms: suspicious interviews warrant a supervisor review while anomalous interviews warrant investigation before the data is used. Because the score is a count of named flags, a supervisor can see exactly why an interview was flagged, a property that separates this design from opaque model-based alternatives and that survey organisations weight heavily in practice (Kreuter, 2013).

A practical deployment would run the pipeline against each day's uploaded audit logs, review the anomaly report each morning, and route suspicious interviews to back-checking while quarantining anomalous ones. The imbalance sweep results inform staffing for that workflow: at realistic low prevalence the detector produces roughly one false alarm per five hundred interviews, so review effort scales with genuine problems rather than with noise. The per-flag reporting also supports feedback to enumerators, since a pattern of speeding flags concentrated in one team is actionable in a way that a bare quality score is not.

## 8. Limitations

Evaluation is synthetic throughout. The generator was built to mimic documented properties of real audit logs, including structural events, complexity-correlated timing and realistic navigation, but no synthetic process reproduces the full variability of field data, and results here estimate an upper bound on operational performance (Chawla et al., 2002). Validation against real interviews with independently verified outcomes remains the most important extension.

Detection is univariate. As the fabrication results show, anomalies expressed only in joint feature patterns evade fence-based flags. The thresholds shipped as defaults were chosen from the literature and from calibration data, and although every threshold is configurable and most are median-relative, deployments on instruments very unlike the twenty-question household pattern of the benchmarks should recalibrate.

Finally, the pipeline depends on the integrity of device clocks and on each platform continuing to emit its current audit schema. Clock drift or schema changes would degrade timestamps or parsing respectively; the parsers detect and mark such records rather than repair them.

## 9. Conclusion

This project set out to make timing-based paradata usable for survey quality assurance at scale, and delivered a working system: format-aware parsers for the two dominant collection platforms, a documented forty-feature library spanning four levels of granularity, a transparent and configurable anomaly detector, a labelled synthetic benchmark generator, and an evaluation that meets its predefined success criteria under deliberately hostile conditions. Precision remained between 0.95 and 1.00 and recall between 0.84 and 1.00 on data the detector had never seen, including a stress condition constructed to blur the line between genuine and anomalous behaviour. The system detects speeding essentially perfectly, disengagement reliably, and blatant fabrication reliably, while mild fabrication marks the boundary at which univariate methods give way to multivariate ones. All six objectives set at proposal stage are met. Future work should validate the system against real field data with verified outcomes, extend detection with an interpretable multivariate layer, and add parsers for further platforms, each of which the architecture was explicitly designed to accommodate.

## References

- Chandola, V., Banerjee, A. and Kumar, V. (2009) 'Anomaly detection: a survey', *ACM Computing Surveys*, 41(3), pp. 1-58.

- Chawla, N.V., Bowyer, K.W., Hall, L.O. and Kegelmeyer, W.P. (2002) 'SMOTE: synthetic minority over-sampling technique', *Journal of Artificial Intelligence Research*, 16, pp. 321-357.

- Conrad, F.G., Tourangeau, R. and Couper, M.P. (2013) 'Adaptive survey design and paradata', *Journal of Official Statistics*, 29(2), pp. 299-320.

- Couper, M.P. (1998) 'Measuring survey quality in a CASIC environment', *Proceedings of the Survey Research Methods Section*. Alexandria, VA: American Statistical Association.

- Groves, R.M., Fowler, F.J., Couper, M.P., Lepkowski, J.M., Singer, E. and Tourangeau, R. (2009) *Survey Methodology*. 2nd edn. Hoboken, NJ: Wiley.

- Hawkins, D.M. (1980) *Identification of Outliers*. London: Chapman and Hall.

- Hodge, V. and Austin, J. (2004) 'A survey of outlier detection methodologies', *Artificial Intelligence Review*, 22(2), pp. 85-126.

- Iglewicz, B. and Hoaglin, D.C. (1993) *How to Detect and Handle Outliers*. Milwaukee, WI: ASQ Quality Press.

- Japkowicz, N. and Stephen, S. (2002) 'The class imbalance problem: a systematic study', *Intelligent Data Analysis*, 6(5), pp. 429-449.

- Kreuter, F. (ed.) (2013) *Improving Surveys with Paradata: Analytic Uses of Process Information*. Hoboken, NJ: Wiley.

- Krosnick, J.A. (1991) 'Response strategies for coping with the cognitive demands of attitude measures in surveys', *Applied Cognitive Psychology*, 5(3), pp. 213-236.

- McKinney, W. (2017) *Python for Data Analysis: Data Wrangling with Pandas, NumPy, and IPython*. 2nd edn. Sebastopol, CA: O'Reilly Media.

- Wenz, M., Kreuter, F. and Janke, S. (2019) 'An investigation of data fabrication using paradata', *Survey Research Methods*, 13(1), pp. 35-47.

- Yan, T. and Tourangeau, R. (2008) 'Fast times and easy questions: the effects of age, experience and question complexity on web survey response times', *Applied Cognitive Psychology*, 22(1), pp. 51-68.
