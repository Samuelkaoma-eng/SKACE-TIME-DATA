# SKACE-Time-Data Paradata Format Guide

**Project:** Automated Extraction and Analysis of Timing-Based Paradata Features for Survey Quality Assurance  
**Student:** Samuel Kaoma (2022016530) · **Course:** CSC 4004 · **Supervisor:** Mr. Mofya Phiri  
**Repository:** https://github.com/Samuelkaoma-eng/SKACE-TIME-DATA  

This guide documents the raw audit-log formats currently handled by the live
pipeline, the normalization rules applied by the parsers, and the resulting
Common Intermediate Representation (CIR).

The authoritative parser implementations are:
- `src/parsers/surveycto_parser.py`
- `src/parsers/odk_parser.py`

> **Synthetic formats, not native exports.** Sections 1 and 2 describe the
> layouts written by the project's synthetic generator, which are the layouts
> the pipeline has been evaluated on. They are not the platforms' native
> exports. ODK Collect's native `audit.csv` has the columns `event`, `node`,
> `start` and `end`, with `start` and `end` in epoch milliseconds, and events
> such as `form start`, `question`, `jump` and `end screen`
> (https://docs.getodk.org/form-audit-log/). SurveyCTO's native text audit is
> by default a per-field summary with `Field name`, `Total duration (seconds)`
> and `First appeared (seconds into survey)`, or, with the `eventlog`
> appearance, an event log with `Device time`, `Form time (ms)`, `Field name`,
> `Event` and `Duration (ms)`
> (https://docs.surveycto.com/02-designing-forms/01-core-concepts/03zd.field-types-text-audit.html).
> ODK's native layout is now supported: automatic detection recognises it by
> its event vocabulary, and `form start`, `end screen`, `form save`,
> `form exit`, `form resume` and `form finalize` are all normalised and
> excluded from the section statistics. This was verified against a log built
> from the documentation, not against a real export. SurveyCTO's native text
> audit is not yet supported in either of its forms.

## 1. SurveyCTO Raw Format

The current synthetic SurveyCTO benchmark exports use these core columns:

| Column | Meaning | Example |
|---|---|---|
| `interview_id` | Interview/session identifier | `INT-00001` |
| `node` | Raw field identifier | `demographics_q01` |
| `event` | Raw event label | `question-end`, `jump` |
| `start` | Event start timestamp in epoch milliseconds | `1711723369086` |
| `end` | Event end timestamp in epoch milliseconds | `1711723381131` |
| `duration_ms` | Raw event duration in milliseconds | `6000` |

Optional metadata columns may also appear, for example:
- `latitude`
- `longitude`
- `accuracy`
- `altitude`

### Parser Behavior

`SurveyCTOParser` applies the following normalization rules:
- `interview_id`
  - uses `interview_id` when present
  - falls back to `uuid` when present
  - otherwise derives sequential synthetic IDs when repeated `form-start` blocks are detected
- `field_name`
  - uses `node` when present
  - falls back to `question_id`
- `event_type`
  - `form-start` -> `form_start`
  - `form-end` and synthetic `end` -> `form_end`
  - `question-start` and synthetic `question` -> `field_start`
  - `question-end` -> `field_end`
  - `constraint` remains `constraint`
- `start_ms` / `end_ms`
  - numeric values are interpreted as epoch milliseconds
  - if numeric values look like epoch seconds, they are multiplied by `1000`
  - non-numeric values are parsed as datetimes and converted to epoch milliseconds
- `duration_ms`
  - uses the raw `duration_ms` column when present
  - otherwise computes `end_ms - start_ms`

## 2. ODK Raw Format

The current synthetic ODK benchmark exports use ODK-style identifiers and ISO
8601 timestamps:

| Column | Meaning | Example |
|---|---|---|
| `instance_id` | Interview/session identifier | `INT-00001` |
| `name` | Raw field identifier | `demographics_q01` |
| `event` | Raw event label | `question-end`, `jump` |
| `start_time` | Event start timestamp as ISO 8601 | `2023-01-02T08:00:06.900+00:00` |
| `end_time` | Event end timestamp as ISO 8601 | `2023-01-02T08:00:12.900+00:00` |

The parser also supports alternative ODK-style names such as:
- `instance_id`
- `name`
- `start_time`
- `end_time`
- `ts_start`
- `ts_end`

### Parser Behavior

`ODKParser` applies the following normalization rules:
- `interview_id`
  - uses `interview_id` when present
  - falls back to `instance_id`
  - otherwise derives sequential synthetic IDs when repeated `form start` blocks are detected
- `field_name`
  - uses the first available column from `node`, `name`, or `field`
- `event_type`
  - `form-start` and `form start` -> `form_start`
  - `question-start`, `question` and `group questions` -> `field_start`
  - `question-end` -> `field_end`
  - `end screen` -> `form_end`
  - `form save`, `form exit`, `form resume` and `form finalize` -> `form_save`,
    `form_exit`, `form_resume` and `form_finalize`, which the section features
    exclude as administrative
- `start_ms` / `end_ms`
  - numeric values are interpreted as epoch milliseconds or epoch seconds
  - ISO 8601 strings are parsed and converted to epoch milliseconds with millisecond precision preserved
- `duration_ms`
  - always computed as `end_ms - start_ms`

## 3. Common Intermediate Representation (CIR)

Both parsers emit the same required CIR schema:

| CIR Column | Type | Meaning |
|---|---|---|
| `interview_id` | string | Unique interview/session identifier |
| `field_name` | string | Normalized raw node or field identifier |
| `event_type` | string | Normalized event label |
| `start_ms` | numeric | Start timestamp in epoch milliseconds |
| `end_ms` | numeric | End timestamp in epoch milliseconds |
| `duration_ms` | numeric | Event duration in milliseconds |

The CIR contract is enforced in `src/parsers/base_parser.py`.

## 4. Practical Notes

- The pipeline currently preserves the raw field/node name in `field_name`
  rather than stripping XPath nodes to their leaf component.
- Section-level features are inferred downstream from `field_name`.
  XPath-like names such as `/data/household/q_name` map to section `household`,
  while root-level names such as `/data/q_name` fall back to `MainSection`.
- The most reliable way to verify parser behavior is:

```bash
python scripts/strict_examiner_audit.py
```

That script checks raw-format consistency, CIR normalization, feature math,
anomaly-score reconstruction, and metric reproducibility end to end.
