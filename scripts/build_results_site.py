"""Build the static results site served by the Docker image.

Runs the pipeline on the shipped synthetic datasets, then writes one HTML page
that reports each run's metrics, detection by anomaly type and flagged
interviews, with every output CSV beside it for download. Nothing on the page
is typed in by hand: change the code, rebuild, and the page follows.

The audit notebook, notebooks/System_Audit_Report.ipynb, is executed against
the n500 SurveyCTO run and rendered as notebook.html beside the page. It runs
in a temporary working folder, so the repository's own output/ is untouched.

    python scripts/build_results_site.py --out build/site

The Dockerfile runs this at build time and serves the result with nginx, so
the hosted site always reports the commit it was built from.
"""

import argparse
import html
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

# label, title, inputs, ground truth, one-line description
RUNS = [
    (
        "sample",
        "Sample data, both formats",
        ["data/odk.csv", "data/surveycto.csv"],
        "data/ground_truth_labels.csv",
        "The 24-interview sample that ships with the repository, SurveyCTO and "
        "ODK logs processed together in one run.",
    ),
    (
        "n500_surveycto",
        "500-interview benchmark, SurveyCTO",
        ["data/synthetic_datasets/n500/audit_logs_surveycto.csv"],
        "data/synthetic_datasets/n500/ground_truth_labels.csv",
        "The canonical benchmark: 400 normal interviews and 100 with injected "
        "fabrication, speeding or disengagement (seed 42).",
    ),
    (
        "n500_odk",
        "500-interview benchmark, ODK",
        ["data/synthetic_datasets/n500/audit_logs_odk.csv"],
        "data/synthetic_datasets/n500/ground_truth_labels.csv",
        "The same 500 interviews written as ODK audit logs, to show the two "
        "parsers agree.",
    ),
]

# The run the audit notebook is executed against.
NOTEBOOK_RUN = "n500_surveycto"
NOTEBOOK = ROOT / "notebooks" / "System_Audit_Report.ipynb"

DOWNLOADS = [
    ("anomaly_report", "Anomaly report"),
    ("predictions", "Predictions against labels"),
    ("feature_dataset", "Per-interview features"),
    ("section_features", "Section-level features"),
    ("question_features", "Question-level features"),
    ("metrics", "Metrics"),
]


def run_pipeline(label: str, inputs: list[str], ground_truth: str, out_dir: Path) -> None:
    command = [
        sys.executable, "run_pipeline.py",
        "--inputs", *inputs,
        "--ground-truth", ground_truth,
        "--label", label,
        "--output-dir", str(out_dir),
    ]
    print(f"Running {label}: {' '.join(command[1:])}", flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


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
        f'<a href="./" style="color:#2563eb">Back to the results</a> &middot; '
        f"This notebook was executed on the <code>{esc(label)}</code> run when the site was "
        "built. Synthetic data only.</div>"
    )
    head_end = body.index(">", body.index("<body")) + 1
    (out / "notebook.html").write_text(body[:head_end] + banner + body[head_end:], encoding="utf-8")


def esc(value) -> str:
    return html.escape(str(value))


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def run_section(label: str, title: str, inputs: list[str], description: str, run_dir: Path) -> str:
    metrics = json.loads((run_dir / f"metrics_{label}.json").read_text())[0]
    by_type = pd.read_csv(run_dir / f"detection_by_type_{label}.csv")
    predictions = pd.read_csv(run_dir / f"predictions_{label}.csv").fillna("")

    tiles = "".join(
        f'<div class="tile"><span class="tile-label">{name}</span>'
        f'<span class="tile-value">{value}</span>'
        f'<span class="tile-note">{note}</span></div>'
        for name, value, note in [
            ("Precision", f"{metrics['precision']:.3f}", f"target {metrics['precision_threshold']}"),
            ("Recall", f"{metrics['recall']:.3f}", f"target {metrics['recall_threshold']}"),
            ("F1", f"{metrics['f1_score']:.3f}", ""),
            ("Specificity", f"{metrics['specificity']:.3f}", ""),
            ("Interviews", f"{metrics['total_samples']}", f"{metrics['anomalies_true']} labelled anomalous"),
        ]
    )

    confusion = (
        '<table class="confusion"><thead><tr><th></th><th>Flagged</th><th>Not flagged</th></tr></thead><tbody>'
        f'<tr><th>Labelled anomalous</th><td>{metrics["true_positive"]}</td><td>{metrics["false_negative"]}</td></tr>'
        f'<tr><th>Labelled normal</th><td>{metrics["false_positive"]}</td><td>{metrics["true_negative"]}</td></tr>'
        "</tbody></table>"
    )

    bars = "".join(
        f'<div class="bar-row"><span class="bar-name">{esc(row.anomaly_type)}</span>'
        f'<span class="bar-track"><span class="bar-fill" style="width:{row.detection_rate * 100:.1f}%"></span></span>'
        f'<span class="bar-value">{int(row.detected)} of {int(row.total)} ({pct(row.detection_rate)})</span></div>'
        for row in by_type.itertuples()
    )

    flagged = predictions[predictions["predicted_is_anomalous"] == 1].sort_values(
        ["anomaly_score", "interview_id"], ascending=[False, True]
    )
    missed = predictions[(predictions["is_anomalous"] == 1) & (predictions["predicted_is_anomalous"] == 0)]

    def rows(frame: pd.DataFrame) -> str:
        return "".join(
            f'<tr class="{"wrong" if row.is_anomalous != row.predicted_is_anomalous else ""}">'
            f"<td>{esc(row.interview_id)}</td><td>{esc(row.anomaly_type)}</td>"
            f"<td>{esc(row.anomaly_category)}</td><td class=\"num\">{esc(row.anomaly_score)}</td>"
            f'<td class="flags">{esc(str(row.flagged_features).replace(",", ", "))}</td></tr>'
            for row in frame.itertuples()
        )

    table_head = (
        "<thead><tr><th>Interview</th><th>Label</th><th>Category</th>"
        '<th class="num">Score</th><th>Flags raised</th></tr></thead>'
    )
    missed_block = (
        f'<details><summary>Labelled anomalous but not flagged ({len(missed)})</summary>'
        f'<div class="scroll"><table>{table_head}<tbody>{rows(missed)}</tbody></table></div></details>'
        if len(missed)
        else ""
    )

    links = "".join(
        f'<li><a href="runs/{label}/{stem}_{label}.csv" download>{name}</a></li>'
        for stem, name in DOWNLOADS
    )
    sources = ", ".join(f"<code>{esc(path)}</code>" for path in inputs)

    return f"""
<section id="{label}">
  <h2>{esc(title)}</h2>
  <p>{esc(description)}</p>
  <p class="muted">Input: {sources}</p>
  <div class="tiles">{tiles}</div>
  <div class="split">
    <div><h3>Confusion matrix</h3>{confusion}</div>
    <div><h3>Detection by anomaly type</h3><div class="bars">{bars}</div></div>
  </div>
  <details><summary>Flagged interviews ({len(flagged)}), highest score first</summary>
    <div class="scroll"><table>{table_head}<tbody>{rows(flagged)}</tbody></table></div>
  </details>
  {missed_block}
  <h3>Download this run</h3>
  <ul class="downloads">{links}</ul>
</section>"""


STYLE = """
:root {
  --bg: #f7f8fa; --surface: #ffffff; --ink: #1f2933; --muted: #5f6b7a;
  --line: #dde3ea; --accent: #2563eb; --accent-soft: #dbe6fd; --warn: #fdecea;
  --banner: #fff7e0; --banner-ink: #6b4e00;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #12161c; --surface: #1a2029; --ink: #e4e8ee; --muted: #9aa5b4;
    --line: #2c3542; --accent: #6b9cff; --accent-soft: #233456; --warn: #3a2224;
    --banner: #2f2814; --banner-ink: #f1d58a;
  }
}
:root[data-theme="dark"] {
  --bg: #12161c; --surface: #1a2029; --ink: #e4e8ee; --muted: #9aa5b4;
  --line: #2c3542; --accent: #6b9cff; --accent-soft: #233456; --warn: #3a2224;
  --banner: #2f2814; --banner-ink: #f1d58a;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink);
  font: 16px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width: 980px; margin: 0 auto; padding: 24px 16px 64px; }
h1 { font-size: 1.8rem; line-height: 1.25; margin: 8px 0 12px; }
h2 { font-size: 1.35rem; margin: 0 0 8px; }
h3 { font-size: 1rem; margin: 20px 0 8px; }
a { color: var(--accent); }
code { font-size: 0.88em; overflow-wrap: anywhere; }
.muted { color: var(--muted); font-size: 0.92rem; }
.banner { background: var(--banner); color: var(--banner-ink); border-radius: 8px;
  padding: 10px 14px; font-size: 0.92rem; margin: 16px 0; }
nav { display: flex; flex-wrap: wrap; gap: 8px; margin: 16px 0 24px; }
nav a { background: var(--accent-soft); border-radius: 999px; padding: 4px 12px;
  text-decoration: none; font-size: 0.9rem; }
section { background: var(--surface); border: 1px solid var(--line); border-radius: 12px;
  padding: 20px; margin: 0 0 20px; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin: 16px 0; }
.tile { border: 1px solid var(--line); border-radius: 8px; padding: 10px 12px; display: flex; flex-direction: column; }
.tile-label { color: var(--muted); font-size: 0.82rem; }
.tile-value { font-size: 1.5rem; font-weight: 600; font-variant-numeric: tabular-nums; }
.tile-note { color: var(--muted); font-size: 0.78rem; min-height: 1em; }
.split { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.4fr); gap: 24px; }
@media (max-width: 720px) { .split { grid-template-columns: minmax(0, 1fr); } }
table { border-collapse: collapse; width: 100%; font-size: 0.88rem; }
th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }
td:first-child { white-space: nowrap; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.confusion td { text-align: right; font-variant-numeric: tabular-nums; font-size: 1rem; }
tr.wrong td { background: var(--warn); }
td.flags { color: var(--muted); font-size: 0.82rem; overflow-wrap: anywhere; }
.bars { display: flex; flex-direction: column; gap: 8px; }
.bar-row { display: grid; grid-template-columns: 90px minmax(0, 1fr) auto; gap: 10px; align-items: center; font-size: 0.88rem; }
.bar-track { background: var(--accent-soft); border-radius: 4px; height: 12px; overflow: hidden; }
.bar-fill { display: block; height: 100%; background: var(--accent); }
.bar-value { font-variant-numeric: tabular-nums; color: var(--muted); white-space: nowrap; }
details { margin-top: 16px; }
summary { cursor: pointer; font-weight: 600; }
.scroll { max-height: 420px; overflow: auto; margin-top: 8px; border: 1px solid var(--line); border-radius: 8px; }
.downloads { display: flex; flex-wrap: wrap; gap: 8px 20px; padding-left: 18px; margin: 0; }
pre { background: var(--surface); border: 1px solid var(--line); border-radius: 8px;
  padding: 12px; overflow-x: auto; font-size: 0.85rem; }
footer { color: var(--muted); font-size: 0.85rem; }
"""


def build_page(sections: list[str], version: str, built: str) -> str:
    nav = "".join(f'<a href="#{label}">{esc(title)}</a>' for label, title, *_ in RUNS)
    nav += '<a href="#notebook">Audit notebook</a>'
    version_text = f"commit <code>{esc(version)}</code>" if version != "unknown" else "an unknown commit"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Paradata Pipeline Results</title>
<meta name="description" content="Live results of the paradata feature extraction pipeline on labelled synthetic survey audit logs.">
<style>{STYLE}</style>
</head>
<body>
<main>
  <p class="muted">Final-year project, Samuel Kaoma</p>
  <h1>Paradata feature extraction pipeline: results</h1>
  <p>Survey platforms such as SurveyCTO and ODK record an audit log of every interview: when each
  question opened, how long it took, when the enumerator went back. This pipeline turns that log into
  forty timing features and uses them to flag interviews that look fabricated, rushed or disengaged,
  naming the features behind every flag.</p>
  <div class="banner">Synthetic data only. Every interview here was generated with a known label, so
  each flag can be checked against the truth. No real respondent data is on this site.</div>
  <p class="muted">Each run below was produced by the pipeline itself when this site was built from
  {version_text} on {esc(built)}. Rows shaded red are interviews the pipeline got wrong.</p>
  <nav>{nav}</nav>
  {"".join(sections)}
  <section id="notebook">
    <h2>Audit notebook</h2>
    <p>The system audit notebook recomputes every anomaly score from the exported features,
    checks it against what the pipeline reported, and plots the score distribution, feature
    correlations and the separation between normal and anomalous interviews. It was executed
    on the 500-interview SurveyCTO run when this site was built.</p>
    <p><a href="notebook.html">Open the executed notebook</a></p>
  </section>
  <section>
    <h2>Reproduce it</h2>
    <p>Every number on this page comes from these commands, run on a fresh copy of the repository:</p>
    <pre>pip install -r requirements.txt
python scripts/build_results_site.py --out build/site</pre>
    <p class="muted">Or one run directly:
    <code>python run_pipeline.py --inputs data/synthetic_datasets/n500/audit_logs_surveycto.csv
    --ground-truth data/synthetic_datasets/n500/ground_truth_labels.csv --label n500_surveycto</code></p>
  </section>
  <footer>Detection is not uniform across anomaly types, and the full validation report (including the
  stress condition where normal and anomalous behaviour overlap) is in <code>docs/validation_report.md</code>
  in the repository.</footer>
</main>
</body>
</html>
"""


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
    (out / "runs").mkdir(parents=True)

    version = args.version.strip() or "unknown"
    built = datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC")

    sections = []
    for label, title, inputs, ground_truth, description in RUNS:
        run_dir = out / "runs" / label
        run_pipeline(label, inputs, ground_truth, run_dir)
        if label == NOTEBOOK_RUN and not args.skip_notebook:
            render_notebook(label, run_dir, out)
        # The combined output repeats the feature dataset and the anomaly
        # report, so it is left out of the downloads.
        (run_dir / f"pipeline_output_{label}.csv").unlink(missing_ok=True)
        sections.append(run_section(label, title, inputs, description, run_dir))

    (out / "index.html").write_text(build_page(sections, version, built), encoding="utf-8")
    (out / "health.json").write_text(
        json.dumps({"status": "ok", "data_mode": "synthetic", "version": version}),
        encoding="utf-8",
    )
    print(f"Site written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
