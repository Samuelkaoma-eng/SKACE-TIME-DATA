#!/usr/bin/env python3
"""
Measure peak memory of the pipeline on the benchmark packs.

Each measurement runs in a fresh Python process, so one dataset's allocations
cannot inflate another's reading. The child process runs the same batch path
as run_pipeline.py (process_batch_detailed, which retains the question- and
section-level tables as well as the interview summaries) and reports its peak
resident set size: the peak working set on Windows, ru_maxrss elsewhere. The
resident size after imports and before any data is read is reported alongside
it, so the data-dependent part can be separated from the interpreter and
library baseline.

Usage:
    python scripts/measure_memory.py --datasets n500 n2000
    python scripts/measure_memory.py --datasets n500 n2000 n10000 --formats surveycto odk
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_ROOT = PROJECT_ROOT / "data" / "synthetic_datasets"
MIB = 1024 * 1024


def markdown_table(frame) -> str:
    """Render a small table as Markdown without the optional tabulate dependency."""
    header = "| " + " | ".join(str(c) for c in frame.columns) + " |"
    rule = "|" + "|".join("---" for _ in frame.columns) + "|"
    body = ["| " + " | ".join(str(v) for v in row) + " |" for row in frame.itertuples(index=False)]
    return "\n".join([header, rule, *body])


def current_rss_bytes() -> int | None:
    try:
        import psutil
    except ImportError:
        return None
    return int(psutil.Process().memory_info().rss)


def peak_rss_bytes() -> int:
    try:
        import psutil

        peak = getattr(psutil.Process().memory_info(), "peak_wset", None)
        if peak is not None:
            return int(peak)
    except ImportError:
        pass
    import resource

    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(usage if sys.platform == "darwin" else usage * 1024)


def child(csv_path: str) -> int:
    sys.path.insert(0, str(PROJECT_ROOT))
    import pandas as pd  # noqa: F401  (imported before the baseline reading)

    from src.pipeline.controller import PipelineController

    baseline = current_rss_bytes()
    started = time.perf_counter()
    detailed = PipelineController(parser_type="auto").process_batch_detailed([Path(csv_path)])
    runtime = time.perf_counter() - started
    print(json.dumps({
        "baseline_rss_bytes": baseline,
        "peak_rss_bytes": peak_rss_bytes(),
        "runtime_seconds": round(runtime, 2),
        "interviews": int(len(detailed["interview_features"])),
        "question_rows": int(len(detailed["question_features"])),
        "section_rows": int(len(detailed["section_features"])),
    }))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--datasets", nargs="+", default=["n500", "n2000"])
    parser.add_argument("--formats", nargs="+", default=["surveycto"], choices=["surveycto", "odk"])
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--child", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.child:
        return child(args.child)

    import pandas as pd

    rows = []
    for dataset in args.datasets:
        for fmt in args.formats:
            csv_path = DATASET_ROOT / dataset / f"audit_logs_{fmt}.csv"
            if not csv_path.exists():
                print(f"Skipping {csv_path.relative_to(PROJECT_ROOT)}: not found", file=sys.stderr)
                continue
            print(f"Measuring {dataset} {fmt} ...", flush=True)
            completed = subprocess.run(
                [sys.executable, __file__, "--child", str(csv_path)],
                cwd=PROJECT_ROOT, capture_output=True, text=True, check=True,
            )
            result = json.loads(completed.stdout.strip().splitlines()[-1])
            baseline = result["baseline_rss_bytes"]
            rows.append({
                "dataset": dataset,
                "format": fmt,
                "interviews": result["interviews"],
                "question_rows": result["question_rows"],
                "section_rows": result["section_rows"],
                "raw_file_mib": round(csv_path.stat().st_size / MIB, 1),
                "baseline_rss_mib": round(baseline / MIB, 1) if baseline else None,
                "peak_rss_mib": round(result["peak_rss_bytes"] / MIB, 1),
                "runtime_seconds": result["runtime_seconds"],
            })
            print(f"  peak {rows[-1]['peak_rss_mib']} MiB, {result['runtime_seconds']} s", flush=True)

    if not rows:
        print("No datasets measured.", file=sys.stderr)
        return 1

    table = pd.DataFrame(rows)
    output_dir = PROJECT_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(output_dir / "memory_profile.csv", index=False)
    (output_dir / "memory_profile.md").write_text(
        "# Peak memory by dataset\n\n"
        f"Platform: {sys.platform}, Python {sys.version.split()[0]}. "
        "Generated by `scripts/measure_memory.py`.\n\n"
        + markdown_table(table) + "\n",
        encoding="utf-8",
    )
    print("\n" + table.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
