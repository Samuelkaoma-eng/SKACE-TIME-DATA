"""Build the two figures embedded in the final academic report.

The per-class recall figure was dropped in revision because it repeated
Table 7; its builder is kept for reference but no longer called.

Every value plotted here is transcribed from a recorded output file under
`output/`; the source is named in the docstring of each builder. Regenerate with:

    python scripts/build_report_figures.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

FIGURE_DIR = Path("report/figures")

INK = "#1f2933"
MUTED = "#6b7785"
GRID = "#dde3ea"
LAYER_FILL = "#e8eef6"
LAYER_EDGE = "#3f6ea8"
ACCENT = "#0f766e"
ACCENT_2 = "#b45309"
ACCENT_3 = "#7c3aed"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9.5,
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK,
        "text.color": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    }
)


def _box(ax, x, y, w, h, title, body, fill=LAYER_FILL, edge=LAYER_EDGE):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.012,rounding_size=0.02",
            linewidth=1.1,
            edgecolor=edge,
            facecolor=fill,
        )
    )
    ax.text(x + w / 2, y + h - 0.028, title, ha="center", va="top", fontsize=10, fontweight="bold")
    ax.text(x + w / 2, y + h - 0.073, body, ha="center", va="top", fontsize=8.2, color=INK, linespacing=1.5)


def _arrow(ax, start, end, color=LAYER_EDGE):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=13,
            linewidth=1.2,
            color=color,
            shrinkA=0,
            shrinkB=0,
        )
    )


def build_architecture(path: Path) -> None:
    """Figure 1. Five-layer pipeline architecture, from section 4 of the report."""
    fig, ax = plt.subplots(figsize=(7.4, 5.9))
    fig.subplots_adjust(left=0.004, right=0.996, top=0.996, bottom=0.004)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    layers = [
        (
            "1. Ingestion",
            "CSV audit logs, one or more files\nCommand line or interactive mode",
        ),
        (
            "2. Parsing",
            "SurveyCTO parser  |  ODK parser  |  automatic format detection\n"
            "Event vocabulary normalisation, timestamp conversion, hybrid file split\n"
            "Output: common intermediate representation, six columns",
        ),
        (
            "3. Feature extraction",
            "Question Q-01 to Q-10   |   Section S-01 to S-10\n"
            "Survey V-01 to V-10   |   Statistical T-01 to T-10\n"
            "Batch stage adds sample-relative features",
        ),
        (
            "4. Validation",
            "Tukey interquartile fences on four features, capped at one point\n"
            "Rule flags from configurable, median-relative thresholds\n"
            "Anomaly score, severity bands, separate data quality flags",
        ),
        (
            "5. Reporting",
            "Feature dataset  |  anomaly report  |  question and section tables\n"
            "Evaluation artefacts when ground truth labels are supplied",
        ),
    ]

    top, height, gap = 0.985, 0.157, 0.026
    for index, (title, body) in enumerate(layers):
        y = top - (index + 1) * height - index * gap
        _box(ax, 0.025, y, 0.95, height, title, body)
        if index:
            _arrow(ax, (0.5, y + height + gap), (0.5, y + height))

    ax.text(
        0.5,
        0.004,
        "The intermediate representation is the only contract between layers 2 and 3, so a new\n"
        "platform needs a new parser and no change anywhere downstream.",
        ha="center",
        va="bottom",
        fontsize=8.3,
        color=MUTED,
        style="italic",
        linespacing=1.5,
    )

    fig.savefig(path, dpi=200)
    plt.close(fig)


def build_prevalence(path: Path) -> None:
    """Figure 2. Class imbalance sweep.

    Source: output/robustness_validation/metrics_sweep_r*.csv, reported in
    section 6.4 of the report and section 4 of the validation report.
    """
    prevalence = [5, 10, 20, 30]
    precision = [0.9615, 1.0000, 1.0000, 1.0000]
    recall = [1.0000, 1.0000, 1.0000, 1.0000]

    fig, ax = plt.subplots(figsize=(6.6, 3.9))
    ax.axhline(0.80, color=ACCENT_2, linewidth=1.0, linestyle=(0, (5, 4)), zorder=1)
    ax.axhline(0.75, color=ACCENT_3, linewidth=1.0, linestyle=(0, (2, 3)), zorder=1)
    ax.text(3.6, 0.806, "proposal precision criterion 0.80", fontsize=7.6, color=ACCENT_2, va="bottom", ha="left")
    ax.text(3.6, 0.756, "proposal recall criterion 0.75", fontsize=7.6, color=ACCENT_3, va="bottom", ha="left")

    ax.plot(prevalence, recall, marker="s", markersize=6.5, linewidth=1.9, color=ACCENT_3, label="Recall", zorder=3)
    ax.plot(prevalence, precision, marker="o", markersize=6.5, linewidth=1.9, color=ACCENT, label="Precision", zorder=4)

    ax.annotate(
        "0.9615\none false positive\nin 500 interviews",
        xy=(5, 0.9615),
        xytext=(7.9, 0.885),
        fontsize=7.8,
        color=INK,
        linespacing=1.4,
        arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=0.9),
    )

    ax.set_xticks(prevalence)
    ax.set_xticklabels([f"{value} %" for value in prevalence])
    ax.set_xlim(3.4, 31.6)
    ax.set_ylim(0.70, 1.035)
    ax.set_xlabel("Anomaly prevalence in the sample")
    ax.set_ylabel("Score")
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="center right", fontsize=8.6, borderaxespad=1.0)
    ax.set_title(
        "Precision and recall against anomaly prevalence\n"
        "Held-out seed 7, canonical difficulty, SurveyCTO, 500 interviews",
        fontsize=9.8,
        loc="left",
        pad=11,
    )

    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def build_per_class(path: Path) -> None:
    """Figure 3. Per-class recall on the held-out stress runs.

    Source: output/robustness_validation/detection_by_type_stress_seed*.csv,
    reported in section 6.6 of the report and section 5 of the validation report.
    """
    runs = ["Seed 7\nSurveyCTO", "Seed 7\nODK", "Seed 99\nSurveyCTO", "Seed 99\nODK", "Aggregate"]
    speeding = [33 / 33, 33 / 33, 33 / 33, 33 / 33, 132 / 132]
    disengaged = [28 / 34, 32 / 34, 30 / 34, 31 / 34, 121 / 136]
    fabricated = [24 / 33, 24 / 33, 25 / 33, 20 / 33, 93 / 132]
    counts = {
        "Speeding": ["33/33", "33/33", "33/33", "33/33", "132/132"],
        "Disengaged": ["28/34", "32/34", "30/34", "31/34", "121/136"],
        "Fabricated": ["24/33", "24/33", "25/33", "20/33", "93/132"],
    }

    positions = list(range(len(runs)))
    width = 0.26
    series = [
        ("Speeding", speeding, -width, ACCENT),
        ("Disengaged", disengaged, 0.0, ACCENT_3),
        ("Fabricated", fabricated, width, ACCENT_2),
    ]

    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    ax.axhline(0.75, color=MUTED, linewidth=1.0, linestyle=(0, (2, 3)), zorder=1)

    for label, values, offset, color in series:
        bars = ax.bar(
            [position + offset for position in positions],
            values,
            width=width,
            label=label,
            color=color,
            zorder=3,
        )
        for bar, annotation in zip(bars, counts[label]):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.016,
                annotation,
                ha="center",
                va="bottom",
                fontsize=7.1,
                color=INK,
            )

    ax.axvline(3.5, color=GRID, linewidth=1.2, zorder=1)

    ax.set_xticks(positions)
    ax.set_xticklabels(runs, fontsize=8.3)
    ax.set_ylim(0, 1.07)
    ax.set_yticks([0.0, 0.25, 0.5, 0.75, 1.0])
    ax.set_ylabel("Per-class recall")
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    criterion_handle = Line2D(
        [], [], color=MUTED, linewidth=1.0, linestyle=(0, (2, 3)), label="Combined-detector recall criterion 0.75"
    )
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles + [criterion_handle],
        labels + [criterion_handle.get_label()],
        frameon=False,
        ncol=2,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.005),
        fontsize=8.4,
        columnspacing=2.4,
        handlelength=1.9,
    )
    ax.set_title(
        "Recall by injected anomaly type, held-out stress evaluation\n"
        "Diagnostic breakdown of one detector, not three separate detectors",
        fontsize=9.8,
        loc="left",
        pad=44,
    )

    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    build_architecture(FIGURE_DIR / "figure1_architecture.png")
    build_prevalence(FIGURE_DIR / "figure2_prevalence.png")
    for figure in sorted(FIGURE_DIR.glob("figure*.png")):
        print(f"wrote {figure}")


if __name__ == "__main__":
    main()
