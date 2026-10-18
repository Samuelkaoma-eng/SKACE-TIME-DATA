"""Build the static results site served by the Docker image.

Runs the pipeline on the shipped synthetic datasets, as a survey team would
run it on a batch of uploads, and writes what each run produced as data for
the review dashboard in site/: every interview with its status, its score and
the reason for each flag in words, its response time per question against the
batch, its raw audit log rows, the pipeline's own console output, and the
output files. The labelled evaluation is written separately, for the page's
validation view, because a team in the field has no labels.

The audit notebook, notebooks/System_Audit_Report.ipynb, is executed against
the n500 SurveyCTO run and rendered as notebook.html. It runs in a temporary
working folder, so the repository's own output/ is untouched.

    python scripts/build_results_site.py --out build/site

The Dockerfile runs this at build time and serves the result with nginx, so
the hosted site always reports the commit it was built from.
"""

import argparse
import html
import json
import math
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.validation.anomaly_detector import AnomalyDetector  # noqa: E402

# label, title, inputs, ground truth, one-line description
RUNS = [
    (
        "sample",
        "Sample batch, both platforms",
        ["data/odk.csv", "data/surveycto.csv"],
        "data/ground_truth_labels.csv",
        "24 interviews uploaded from SurveyCTO and ODK together, including six broken records.",
    ),
    (
        "n500_surveycto",
        "500 interviews, SurveyCTO",
        ["data/synthetic_datasets/n500/audit_logs_surveycto.csv"],
        "data/synthetic_datasets/n500/ground_truth_labels.csv",
        "A survey-sized batch exported from SurveyCTO.",
    ),
    (
        "n500_odk",
        "500 interviews, ODK",
        ["data/synthetic_datasets/n500/audit_logs_odk.csv"],
        "data/synthetic_datasets/n500/ground_truth_labels.csv",
        "The same 500 interviews exported from ODK Collect.",
    ),
]

# A harder batch, regenerated at build time from its recorded seed: held-out
# seed 7 at stress difficulty, where some genuine interviews are fast with little
# navigation and some fabrications are only mildly compressed, so the queue has
# review cases, false alarms and misses. The generated files stay in a temporary
# folder; pages show the path the project's robustness script uses for them.
STRESS_SEED = 7
STRESS_SHOWN = "data/robustness_checks/n500_seed7_stress"
SHOWN_PREFIXES: dict[str, str] = {}

# The run the audit notebook is executed against.
NOTEBOOK_RUN = "n500_surveycto"
NOTEBOOK = ROOT / "notebooks" / "System_Audit_Report.ipynb"

# Output files shown in the page's output view, in the order a user would open them.
OUTPUT_FILES = [
    ("anomaly_report", "Anomaly report", "One row per interview: score, status and the flags that fired."),
    ("feature_dataset", "Interview features", "The 40 timing features for every interview."),
    ("section_features", "Section features", "Timing per interview and section."),
    ("question_features", "Question features", "Timing per interview and question."),
    ("predictions", "Predictions against labels", "Validation only: each prediction beside its label."),
    ("metrics", "Metrics", "Validation only: precision, recall and the acceptance checks."),
]

# Features shown beside the batch median on an interview's page.
KEY_FEATURES = [
    ("V-01_total_interview_duration_ms", "Total duration", "ms"),
    ("T-06_rt_mean", "Mean response time", "ms"),
    ("T-07_rt_median", "Median response time", "ms"),
    ("T-02_rt_iqr", "Response time IQR", "ms"),
    ("T-03_rt_entropy", "Response time entropy", "num"),
    ("T-08_rt_cv", "Coefficient of variation", "num"),
    ("V-06_back_navigation_total_count", "Back-navigations", "int"),
    ("V-05_back_navigation_rate", "Back-navigation rate", "pct"),
    ("S-07_mean_pause_duration_ms", "Mean pause", "ms"),
    ("S-08_max_pause_duration_ms", "Longest pause", "ms"),
    ("S-06_pause_count_30s", "Pauses over 30 s", "int"),
    ("V-09_session_length_vs_median", "Length against batch median", "ratio"),
]


ZERO_IS_REAL = [
    "V-06_back_navigation_total_count", "V-05_back_navigation_rate",
    "S-06_pause_count_30s", "V-09_session_length_vs_median",
]


def shown(text: str) -> str:
    """Replace build-time temporary paths with the paths a user would type."""
    for real, display in SHOWN_PREFIXES.items():
        text = text.replace(real, display).replace(real.replace("\\", "/"), display)
        text = text.replace(display + "\\", display + "/")
    return text


def secs(ms) -> str:
    """Format milliseconds for a reader: 1.2 s, 46 s, 3.1 min."""
    if ms is None or (isinstance(ms, float) and math.isnan(ms)):
        return "n/a"
    s = float(ms) / 1000
    if abs(s) >= 120:
        return f"{s / 60:.1f} min"
    if abs(s) >= 10:
        return f"{s:.0f} s"
    return f"{s:.1f} s"


def num(v, digits=2) -> str:
    return "n/a" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{float(v):.{digits}f}"


def positive_median(series: pd.Series):
    values = pd.to_numeric(series, errors="coerce")
    values = values[values > 0]
    return float(values.median()) if not values.empty else None


def tukey(series: pd.Series, k: float):
    values = pd.to_numeric(series, errors="coerce")
    q1, q3 = values.quantile(0.25), values.quantile(0.75)
    return q1 - k * (q3 - q1), q3 + k * (q3 - q1)


def explain(flag: str, r: dict, b: dict, d: AnomalyDetector) -> tuple[str, str, str]:
    """Return (kind, short label, sentence) for one flag on one interview.

    Each sentence restates the detector's rule with this interview's value and
    the batch value it was compared against, so the reason can be checked.
    """
    v = r.get
    rules = {
        "flag_too_fast": ("rule", "Too fast overall",
                          f"The whole interview took {secs(v('V-01_total_interview_duration_ms'))}, under the "
                          f"{secs(d.too_fast_ms)} floor."),
        "flag_too_slow": ("rule", "Too slow overall",
                          f"The whole interview took {secs(v('V-01_total_interview_duration_ms'))}, over the "
                          f"{secs(d.too_slow_ms)} ceiling."),
        "flag_short_relative_duration": ("rule", "Short for this batch",
                                         f"It took {num(v('V-09_session_length_vs_median'))} times the batch's "
                                         f"median length; the rule fires below {d.short_session_median_ratio}."),
        "flag_low_mean_rt": ("rule", "Answers too fast",
                             f"Mean response time {secs(v('T-06_rt_mean'))} is under half the batch median of "
                             f"{secs(b['T-06_rt_mean'])}."),
        "flag_low_entropy": ("rule", "Same time on every question",
                             f"Response-time entropy is {num(v('T-03_rt_entropy'))}, under {d.low_entropy_threshold}: "
                             "almost every answer fell in the same one-second band."),
        "flag_uniform_timing": ("rule", "Uniform pacing",
                                f"Coefficient of variation {num(v('T-08_rt_cv'), 3)} is under {d.uniform_timing_cv}: "
                                "easy and hard questions took the same time."),
        "flag_low_rt_iqr": ("rule", "Compressed spread",
                            f"The spread of response times (IQR {secs(v('T-02_rt_iqr'))}) is at most half the batch "
                            f"median of {secs(b['T-02_rt_iqr'])}, alongside uniform timing."),
        "flag_low_section_variance": ("rule", "Flat within sections",
                                      "Timing barely varies inside each section: "
                                      f"{100 * (v('S-03_within_section_variance') or 0) / b['S-03_within_section_variance']:.1f} "
                                      "percent of the batch median, under the 25 percent rule, alongside compressed timing."),
        "flag_zero_back_nav": ("rule", "Never went back",
                               "No back-navigation at all, together with compressed timing."),
        "flag_high_back_nav": ("rule", "Went back very often",
                               f"Went back on {100 * (v('V-05_back_navigation_rate') or 0):.0f} percent of questions, "
                               f"at or above {d.high_back_nav_rate_threshold:.0%}."),
        "flag_moderate_back_nav": ("rule", "Went back often",
                                   f"Went back on {100 * (v('V-05_back_navigation_rate') or 0):.0f} percent of questions, "
                                   f"at or above {d.moderate_back_nav_rate_threshold:.0%}."),
        "flag_long_pause_relative": ("rule", "Long pause",
                                     f"The longest pause, {secs(v('S-08_max_pause_duration_ms'))}, is at least "
                                     f"{d.long_pause_median_ratio:g} times the batch median of "
                                     f"{secs(b['S-08_max_pause_duration_ms'])}."),
        "flag_elevated_pause": ("rule", "Pauses between questions",
                                f"The mean pause between questions, {secs(v('S-07_mean_pause_duration_ms'))}, is at "
                                f"least {d.elevated_pause_median_ratio:g} times the batch median of "
                                f"{secs(b['S-07_mean_pause_duration_ms'])}."),
        "flag_rule_pause": ("rule", "Repeated long pauses",
                            f"{int(v('S-06_pause_count_30s') or 0)} pauses over 30 s, the longest "
                            f"{secs(v('S-08_max_pause_duration_ms'))}."),
        "flag_iqr_duration": ("iqr", "Unusual total duration",
                              f"Total duration {secs(v('V-01_total_interview_duration_ms'))} is outside the batch's fences "
                              f"of {secs(b['fence_V-01'][0])} to {secs(b['fence_V-01'][1])}."),
        "flag_iqr_rt_mean": ("iqr", "Unusual mean response time",
                             f"Mean response time {secs(v('T-06_rt_mean'))} is outside the batch's fences of "
                             f"{secs(b['fence_T-06'][0])} to {secs(b['fence_T-06'][1])}."),
        "flag_iqr_entropy": ("iqr", "Unusual entropy",
                             f"Entropy {num(v('T-03_rt_entropy'))} is outside the batch's fences of "
                             f"{num(b['fence_T-03'][0])} to {num(b['fence_T-03'][1])}."),
        "flag_iqr_variance": ("iqr", "Unusual variance",
                              "Response-time variance is outside the batch's fences."),
        "flag_invalid_ratio": ("dq", "Speed trajectory missing",
                               "The early and late pace could not be computed from this record."),
        "flag_missing_data": ("dq", "No response times",
                              "No usable response times were recorded."),
        "flag_inconsistent_metrics": ("dq", "Timings contradict each other",
                                      "Recorded times are inconsistent, for example a question longer than its section."),
    }
    return rules.get(flag, ("rule", flag, flag))


def clean(value):
    """JSON-safe scalar."""
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if hasattr(value, "item"):
        value = value.item()
    return value


def run_pipeline(label: str, inputs: list[str], ground_truth: str, out_dir: Path) -> tuple[str, float]:
    command = [
        sys.executable, "run_pipeline.py",
        "--inputs", *inputs,
        "--ground-truth", ground_truth,
        "--label", label,
        "--output-dir", str(out_dir),
    ]
    print(f"Running {label}: {' '.join(command[1:])}", flush=True)
    started = time.perf_counter()
    result = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
    seconds = time.perf_counter() - started
    print(result.stdout, flush=True)
    # Show the log as a user would see it in the project folder, not with this
    # build's absolute paths.
    log = result.stdout.replace(str(out_dir), "output").replace(str(ROOT) + os.sep, "")
    log = log.replace("\\", "/") if os.sep == "\\" else log
    command_line = shown("python run_pipeline.py --inputs " + " ".join(inputs) +
                         f" --ground-truth {ground_truth} --label {label}")
    return f"$ {command_line}\n{shown(log).strip()}\n", seconds


def batch_data(label, title, inputs, ground_truth, description, run_dir, log, seconds):
    detector = AnomalyDetector()
    report = pd.read_csv(run_dir / f"anomaly_report_{label}.csv").fillna({"flagged_features": ""})
    features = pd.read_csv(run_dir / f"feature_dataset_{label}.csv")
    questions = pd.read_csv(run_dir / f"question_features_{label}.csv")
    predictions = pd.read_csv(run_dir / f"predictions_{label}.csv")
    metrics = json.loads((run_dir / f"metrics_{label}.json").read_text())[0]
    by_type = pd.read_csv(run_dir / f"detection_by_type_{label}.csv")

    # The batch statistics the rules compare against.
    # The detector takes its medians over positive values only, so broken
    # records do not drag them down; the explanations quote the same numbers.
    # Counts, rates and the length ratio keep their zeros, which are real.
    batch = {name: positive_median(features[name]) for name, _, _ in KEY_FEATURES if name in features}
    for name in ZERO_IS_REAL:
        batch[name] = clean(float(pd.to_numeric(features[name], errors="coerce").median()))
    batch["S-03_within_section_variance"] = positive_median(features["S-03_within_section_variance"])
    batch["fence_V-01"] = tukey(features["V-01_total_interview_duration_ms"], detector.iqr_multiplier)
    batch["fence_T-06"] = tukey(features["T-06_rt_mean"], detector.iqr_multiplier)
    batch["fence_T-03"] = tukey(features["T-03_rt_entropy"], detector.iqr_multiplier)

    question_order = list(dict.fromkeys(questions["field_name"].dropna()))
    rt = questions.pivot_table(index="interview_id", columns="field_name",
                               values="Q-01_response_time_ms", aggfunc="first")
    rt = rt.reindex(columns=question_order)
    batch_rt = [clean(x) for x in rt.median(axis=0, skipna=True).tolist()]

    feature_rows = features.set_index("interview_id").to_dict("index")
    interviews = []
    for row in report.itertuples(index=False):
        f = feature_rows.get(row.interview_id, {})
        flags = [x for x in str(row.flagged_features).split(",") if x]
        explained = []
        for flag in flags:
            kind, short, sentence = explain(flag, f, batch, detector)
            explained.append({"flag": flag, "kind": kind, "label": short, "text": sentence})
        series = rt.loc[row.interview_id].tolist() if row.interview_id in rt.index else []
        interviews.append({
            "id": row.interview_id,
            "file": row.file_name,
            "status": row.status,
            "category": row.anomaly_category,
            "score": int(row.anomaly_score),
            "iqr": int(row.iqr_flags),
            "rule": int(row.rule_flags),
            "dq": int(row.is_data_quality_issue),
            "flags": explained,
            "f": {name: clean(f.get(name)) for name, _, _ in KEY_FEATURES},
            "rt": [clean(x) for x in series],
        })

    counts = report["status"].value_counts().to_dict()
    dq = int(report["is_data_quality_issue"].sum())
    flagged_behaviour = int(((report["status"] == "FLAGGED") & (report["is_data_quality_issue"] == 0)).sum())

    raw_rows = 0
    platforms = []
    for path in inputs:
        frame = pd.read_csv(ROOT / path)
        raw_rows += len(frame)
        platforms.append("ODK" if "instance_id" in frame.columns else "SurveyCTO")

    files = []
    for stem, name, note in OUTPUT_FILES:
        path = run_dir / f"{stem}_{label}.csv"
        if path.exists():
            frame = pd.read_csv(path)
            files.append({"stem": stem, "name": name, "note": note,
                          "path": f"runs/{label}/{path.name}",
                          "rows": len(frame), "columns": len(frame.columns),
                          "bytes": path.stat().st_size})

    truth = predictions.set_index("interview_id")["anomaly_type"].to_dict()
    return {
        "label": label,
        "title": title,
        "description": description,
        "inputs": [shown(p) for p in inputs],
        "platforms": sorted(set(platforms)),
        "raw_rows": raw_rows,
        "seconds": round(seconds, 1),
        "log": log,
        "thresholds": {"review": detector.behavior_score_threshold,
                       "flagged": detector.anomalous_score_threshold},
        "counts": {
            "total": len(report),
            "clean": int(counts.get("CLEAN", 0)),
            "review": int(counts.get("REVIEW", 0)),
            "flagged": flagged_behaviour,
            "dq": dq,
        },
        "questions": question_order,
        "batch_rt": batch_rt,
        "batch": {name: clean(batch.get(name)) for name, _, _ in KEY_FEATURES},
        "key_features": [{"name": n, "label": l, "unit": u} for n, l, u in KEY_FEATURES],
        "interviews": interviews,
        "files": files,
        "validation": {
            "metrics": {k: clean(v) for k, v in metrics.items()},
            "by_type": [{k: clean(v) for k, v in r.items()} for r in by_type.to_dict("records")],
            "truth": truth,
        },
    }


def raw_data(inputs: list[str]) -> dict:
    """Every raw audit log row, grouped by interview, for the interview view."""
    out = {}
    for path in inputs:
        frame = pd.read_csv(ROOT / path, dtype=str).fillna("")
        key = "interview_id" if "interview_id" in frame.columns else "instance_id"
        columns = list(frame.columns)
        for interview_id, group in frame.groupby(key, sort=False):
            out[interview_id] = {"file": Path(path).name, "columns": columns,
                                 "rows": group.values.tolist()}
    return out


def render_notebook(label: str, run_dir: Path, out: Path) -> None:
    """Execute the audit notebook on one run and write it as notebook.html."""
    import tempfile

    import nbformat
    from nbconvert import HTMLExporter
    from nbconvert.preprocessors import ExecutePreprocessor

    print(f"Executing the audit notebook on {label}", flush=True)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        # The notebook takes the folder holding src/ as the project root and
        # reads the run's tables from output/ there.
        shutil.copytree(ROOT / "src", work / "src", ignore=shutil.ignore_patterns("__pycache__"))
        (work / "output").mkdir()
        for stem in ("pipeline_output", "question_features", "section_features"):
            shutil.copy(run_dir / f"{stem}_{label}.csv", work / "output")

        notebook = nbformat.read(NOTEBOOK, as_version=4)
        os.environ["SKACE_NOTEBOOK_RUN_LABEL"] = label
        # The inline backend puts each figure into the notebook. A non-interactive
        # backend such as Agg, the default where there is no display, would
        # leave plt.show() drawing nothing.
        os.environ["MPLBACKEND"] = "module://matplotlib_inline.backend_inline"
        ExecutePreprocessor(timeout=600, kernel_name="python3").preprocess(
            notebook, {"metadata": {"path": str(work)}}
        )

    body, _ = HTMLExporter(template_name="lab").from_notebook_node(notebook)
    banner = (
        '<div style="font:15px/1.5 system-ui,sans-serif;padding:10px 16px;'
        'background:#fff7e0;color:#6b4e00;border-bottom:1px solid #e8d9a8">'
        '<a href="./#validation" style="color:#2563eb">Back to the dashboard</a> &middot; '
        f"This notebook was executed on the <code>{html.escape(label)}</code> batch when the site was "
        "built. Synthetic data only.</div>"
    )
    head_end = body.index(">", body.index("<body")) + 1
    (out / "notebook.html").write_text(body[:head_end] + banner + body[head_end:], encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the static results site.")
    parser.add_argument("--out", default="build/site", help="Directory to write the site into")
    parser.add_argument(
        "--version",
        default=os.environ.get("BUILD_VERSION", ""),
        help="Commit the site is built from, shown on the page and at /health",
    )
    parser.add_argument("--skip-notebook", action="store_true", help="Do not execute the audit notebook")
    args = parser.parse_args()

    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / "site", out)
    (out / "runs").mkdir()
    (out / "data").mkdir()

    version = args.version.strip() or "unknown"
    built = datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC")

    import tempfile

    generated = tempfile.TemporaryDirectory()
    stress_dir = Path(generated.name)
    subprocess.run(
        [sys.executable, "tests/generate_benchmark_datasets.py", "--dataset-size", "500",
         "--seed", str(STRESS_SEED), "--difficulty", "stress", "--output-dir", str(stress_dir)],
        cwd=ROOT, check=True, capture_output=True, text=True)
    SHOWN_PREFIXES[str(stress_dir)] = STRESS_SHOWN
    runs = RUNS + [(
        "stress_seed7_surveycto",
        "500 interviews, harder batch",
        [str(stress_dir / "audit_logs_surveycto.csv")],
        str(stress_dir / "ground_truth_labels.csv"),
        "Held-out seed 7 at stress difficulty: some genuine interviews are fast, some fabrications are mild, "
        "so the queue has review cases, false alarms and misses.",
    )]

    index = []
    for label, title, inputs, ground_truth, description in runs:
        run_dir = out / "runs" / label
        log, seconds = run_pipeline(label, inputs, ground_truth, run_dir)
        if label == NOTEBOOK_RUN and not args.skip_notebook:
            render_notebook(label, run_dir, out)
        data = batch_data(label, title, inputs, ground_truth, description, run_dir, log, seconds)
        (out / "data" / f"{label}.json").write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
        (out / "data" / f"raw_{label}.json").write_text(
            json.dumps(raw_data(inputs), separators=(",", ":")), encoding="utf-8")
        # The combined output repeats the feature dataset and the anomaly
        # report, so it is not published.
        (run_dir / f"pipeline_output_{label}.csv").unlink(missing_ok=True)
        index.append({"label": label, "title": title, "description": description,
                      "total": data["counts"]["total"], "platforms": data["platforms"]})

    (out / "data" / "index.json").write_text(json.dumps({
        "batches": index, "version": version, "built": built,
        "notebook": NOTEBOOK_RUN if not args.skip_notebook else None,
    }), encoding="utf-8")
    (out / "health.json").write_text(
        json.dumps({"status": "ok", "data_mode": "synthetic", "version": version}),
        encoding="utf-8",
    )
    print(f"Site written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
