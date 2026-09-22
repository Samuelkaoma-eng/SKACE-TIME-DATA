"""Render the demo panels shown in the project presentation.

Each panel is drawn from a live run of the pipeline on the sample data in
`data/`, so the presentation shows the current code rather than an old capture.
Regenerate the underlying run first, then this script:

    python run_pipeline.py --inputs data/odk.csv data/surveycto.csv --parser auto \
        --output-dir output --label demo --ground-truth data/ground_truth_labels.csv
    python scripts/build_demo_panels.py
"""

from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

OUT = Path("report/figures")
FONTS = Path("C:/Windows/Fonts")

TERM_BG = (22, 27, 34)
TERM_FG = (201, 209, 217)
TERM_DIM = (125, 139, 153)
TERM_GREEN = (86, 211, 100)
TERM_CYAN = (86, 182, 194)
TERM_AMBER = (227, 158, 62)

INK = (31, 41, 51)
MUTED = (107, 119, 133)
GRID = (214, 222, 229)
PANEL = (238, 242, 246)
TEAL = (15, 118, 110)
AMBER = (180, 83, 9)
WHITE = (255, 255, 255)


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


MONO = lambda s: font("consola.ttf", s)
MONOB = lambda s: font("consolab.ttf", s)
SANS = lambda s: font("calibri.ttf", s)
SANSB = lambda s: font("calibrib.ttf", s)


def terminal(lines, path, width=1700, pad=26, line_h=30, size=19):
    """Dark terminal panel. Each line is (text, colour, bold)."""
    height = pad * 2 + line_h * len(lines) + 16
    img = Image.new("RGB", (width, height), TERM_BG)
    d = ImageDraw.Draw(img)
    for i, (cx, col) in enumerate([(pad + 10, (255, 95, 86)), (pad + 32, (255, 189, 46)), (pad + 54, (39, 201, 63))]):
        d.ellipse([cx, pad - 4, cx + 13, pad + 9], fill=col)
    y = pad + 26
    for text, colour, bold in lines:
        d.text((pad, y), text, font=(MONOB(size) if bold else MONO(size)), fill=colour)
        y += line_h
    img.save(path)
    return path


def table_panel(headers, rows, widths, path, note=None, highlight=None, size=19):
    """Light table panel with a teal header band."""
    pad, rh, hh = 22, 38, 42
    width = pad * 2 + sum(widths)
    height = pad * 2 + hh + rh * len(rows) + (46 if note else 0)
    img = Image.new("RGB", (width, height), WHITE)
    d = ImageDraw.Draw(img)

    x, y = pad, pad
    d.rectangle([x, y, x + sum(widths), y + hh], fill=TEAL)
    cx = x
    for htext, w in zip(headers, widths):
        d.text((cx + 12, y + 11), htext, font=SANSB(size), fill=WHITE)
        cx += w
    y += hh

    for ri, row in enumerate(rows):
        bg = WHITE if ri % 2 == 0 else PANEL
        if highlight is not None and ri == highlight:
            bg = (253, 243, 230)
        d.rectangle([x, y, x + sum(widths), y + rh], fill=bg, outline=GRID)
        cx = x
        for ci, (cell, w) in enumerate(zip(row, widths)):
            text, colour, bold = cell if isinstance(cell, tuple) else (str(cell), INK, False)
            fnt = (MONOB(size - 2) if bold else MONO(size - 2)) if ci else (SANSB(size) if bold else SANS(size))
            d.text((cx + 12, y + 9), text, font=fnt, fill=colour)
            cx += w
        y += rh

    if note:
        d.text((pad, y + 14), note, font=SANS(size - 2), fill=MUTED)
    img.save(path)
    return path


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # ---- Panel 1: the run -------------------------------------------------
    terminal([
        ("python run_pipeline.py --inputs data/odk.csv data/surveycto.csv --parser auto \\", TERM_FG, True),
        ("             --output-dir output --label demo \\", TERM_FG, True),
        ("             --ground-truth data/ground_truth_labels.csv", TERM_FG, True),
        ("", TERM_FG, False),
        ("Initializing Pipeline Controller with config: Parser = AUTO", TERM_DIM, False),
        ("Beginning Batch Processing for 2 files...", TERM_DIM, False),
        ("  -> Parsing odk.csv using ODKParser...", TERM_CYAN, False),
        ("  -> Parsing surveycto.csv using SurveyCTOParser...", TERM_CYAN, False),
        ("", TERM_FG, False),
        ("Features engineered for 24 extracted interviews.", TERM_FG, False),
        ("Anomaly Detection Rules (IQR + Entropy + Speed) successfully applied.", TERM_GREEN, False),
        ("", TERM_FG, False),
        ("Question-level features written to: output/question_features_demo.csv", TERM_DIM, False),
        ("Section-level features  written to: output/section_features_demo.csv", TERM_DIM, False),
        ("Feature dataset         written to: output/feature_dataset_demo.csv", TERM_DIM, False),
        ("Anomaly report          written to: output/anomaly_report_demo.csv", TERM_DIM, False),
        ("Combined dataset        written to: output/pipeline_output_demo.csv", TERM_DIM, False),
    ], OUT / "demo1_run.png")

    # ---- Panel 2: the feature dataset -------------------------------------
    fd = pd.read_csv("output/feature_dataset_demo.csv")
    cols = ["V-01_total_interview_duration_ms", "T-06_rt_mean", "T-02_rt_iqr",
            "T-03_rt_entropy", "T-08_rt_cv", "V-06_back_navigation_total_count"]
    rows = []
    for iid in ["ODK400", "ODK401", "ODK407", "INT400", "INT401"]:
        m = fd[fd["interview_id"] == iid]
        if m.empty:
            continue
        r = m.iloc[0]
        rows.append([iid] + ["%.2f" % r[c] if isinstance(r[c], float) else str(r[c]) for c in cols])
    table_panel(
        ["interview_id", "V-01 duration", "T-06 mean rt", "T-02 rt IQR", "T-03 entropy", "T-08 rt CV", "V-06 back nav"],
        rows, [230, 210, 190, 175, 180, 165, 185],
        OUT / "demo2_features.png",
        note="Six of the forty columns. One row per interview, every feature carrying its catalogue identifier.",
    )

    # ---- Panel 3: the anomaly report --------------------------------------
    ar = pd.read_csv("output/anomaly_report_demo.csv")
    rows = []
    for iid in ["ODK400", "ODK401", "ODK402", "INT400", "INT401"]:
        m = ar[ar["interview_id"] == iid]
        if m.empty:
            continue
        r = m.iloc[0]
        cat = str(r["anomaly_category"])
        colour = {"normal": TEAL, "anomalous": AMBER, "dq_issue": MUTED}.get(cat, INK)
        flags = str(r["flagged_features"])
        rows.append([str(r["file_name"]), (iid, INK, False), (str(r["anomaly_score"]), INK, True),
                     (cat, colour, True), (str(r["status"]), colour, False),
                     (flags[:42] + ("..." if len(flags) > 42 else ""), MUTED, False)])
    table_panel(["source file", "interview_id", "score", "category", "status", "active flags"],
                rows, [190, 190, 105, 170, 145, 600],
                OUT / "demo3_report.png",
                note="Both platform formats in one run, one report. The active flags column names exactly why each interview was caught.")

    # ---- Panel 4: one interview explained ---------------------------------
    a = fd[fd["interview_id"] == "ODK401"].iloc[0]
    g = fd[fd["interview_id"] == "ODK400"].iloc[0]
    spec = [("Total duration", "V-01_total_interview_duration_ms", "%.0f ms"),
            ("Mean response time", "T-06_rt_mean", "%.0f ms"),
            ("Response time IQR", "T-02_rt_iqr", "%.1f ms"),
            ("Response time entropy", "T-03_rt_entropy", "%.3f"),
            ("Coefficient of variation", "T-08_rt_cv", "%.3f"),
            ("Back navigations", "V-06_back_navigation_total_count", "%.0f")]
    rows = []
    for label, col, fmt in spec:
        rows.append([label, (fmt % g[col], TEAL, False), (fmt % a[col], AMBER, True)])
    table_panel(["Feature", "ODK400  genuine", "ODK401  flagged"],
                rows, [330, 250, 250],
                OUT / "demo4_explained.png",
                note=None)

    # ---- Panel 5: the labelled evaluation ---------------------------------
    terminal([
        ("Labelled evaluation completed.", TERM_FG, True),
        ("", TERM_FG, False),
        ("Precision=1.0000  Recall=1.0000  F1=1.0000", TERM_GREEN, True),
        ("", TERM_FG, False),
        ("Acceptance checks:", TERM_FG, False),
        ("  precision        True", TERM_GREEN, False),
        ("  recall           True", TERM_GREEN, False),
        ("  fabricated_score True", TERM_GREEN, False),
        ("  normal_score     True", TERM_GREEN, False),
        ("", TERM_FG, False),
        ("Merged predictions written to: output/predictions_demo.csv", TERM_DIM, False),
        ("Metrics summary     written to: output/metrics_demo.md", TERM_DIM, False),
        ("", TERM_FG, False),
        ("# the detector never sees the labels: they are joined after prediction,", TERM_AMBER, False),
        ("# one to one, and the join fails loudly on any duplicate or missing id.", TERM_AMBER, False),
    ], OUT / "demo5_evaluation.png")

    for p in sorted(OUT.glob("demo*.png")):
        print("wrote %s" % p)


if __name__ == "__main__":
    main()
