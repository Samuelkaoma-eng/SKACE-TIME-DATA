# SKACE-Time-Data: Paradata Format & Parsing Guide

This document satisfies the seed project requirement for a **Paradata Format Guide**, detailing the structures of `SurveyCTO` and `ODK Collect` audit logs, mapping differences, and the parsing strategies employed to achieve a Common Intermediate Representation (CIR).

---

## 1. SurveyCTO Format Structure

SurveyCTO provides natively detailed paradata with explicit temporal boundaries for each interaction.

### Field Naming Conventions (Raw)
*   **`event type`**: Natively explicitly categorizes events (e.g., `form start`, `question`, `back`).
*   **`duration`**: A pre-calculated numeric field representing milliseconds spent on the event.
*   **`timestamp`**: Unix timestamp in milliseconds indicating event conclusion.
*   **`field`**: The specific survey question or node ID.
*   **`old value` / `new value`**: Tracks the mutated state for edit-counting.

### Parsing Strategy
`SurveyCTOParser.py` normalizes this structured input directly:
1.  **Lowercasing Keys**: Protects against unexpected capitalization changes by vendors (`Event Type` -> `event_type`).
2.  **Explicit Mapping**: `duration` translates identically to `duration_ms`.
3.  **Time Deduction**: The start bounding is calculated algebraically via `timestamp - duration`.

---

## 2. ODK Collect Format Structure

ODK Collect employs a sparser, distinct vocabulary requiring complex inference to match SurveyCTO.

### Field Naming Conventions (Raw)
*   **`event`**: Equivalent to SurveyCTO's `event type`.
*   **`node`**: Equivalent to SurveyCTO's `field`.
*   **`start` / `end`**: Absolute ISO 8601 timestamp strings (e.g., `2024-05-14T10:20:30.123Z`) instead of numeric durations.
*   **`old-value` / `new-value`**: Uses hyphens instead of spaces.

### Event Mapping Discrepancies
ODK utilizes fundamentally different nomenclature for navigation:
*   `jump`: Can signify random navigation *or* backwards movement (must be mathematically or historically inferred, whereas SurveyCTO natively provides `back`).
*   `hierarchy`: Unique to ODK groupings.

### Parsing Strategy
`ODKParser.py` implements a translation layer to enforce CIR:
1.  **Datetime extraction**: Forces `pd.to_datetime()` uniformly to `datetime64[ms]` to enforce millisecond precision parity with SurveyCTO.
2.  **Duration Inference**: Calculates `end_ms - start_ms` dynamically since ODK does not provide a standalone `duration_ms` column.
3.  **Vocabulary Normalization**:
    *   `node` -> `field_name`
    *   `event` -> `event_type`
    *   `old-value` -> `old_value`

---

## 3. The Common Intermediate Representation (CIR)

Both parsers yield identical, strictly typed Python DataFrames enforcing the **CIR Schema**. This mathematically guarantees that downstream feature extraction (`QuestionFeatureExtractor`, `SurveyFeatureExtractor`) does not care whether the root application was SurveyCTO or ODK Collect.

**CIR Core Fields:**
*   `interview_id` (str)
*   `start_ms` (Int64)
*   `end_ms` (Int64)
*   `duration_ms` (Int64)
*   `event_type` (str)
*   `field_name` (str)
*   `new_value` (str)
