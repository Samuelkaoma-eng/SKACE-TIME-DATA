"""Fill the page numbers in the report's contents, tables and figures lists.

The three lists at the front of the report are written by hand in markdown, so
they cannot know what page anything lands on. This script measures it: build the
Word document, export it to PDF through Word itself, find the page each heading
and each caption starts on, and write those numbers back into the markdown.

Writing the numbers in can move the text slightly, so the measurement is
repeated until two consecutive rounds agree.

Usage:

    python scripts/paginate_report.py            # update markdown, docx and PDF
    python scripts/paginate_report.py --check    # fail if the numbers are stale

Requires Microsoft Word, pdfplumber, and the same toolchain as
`scripts/build_docx_deliverables.py`.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pdfplumber

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "report/final_academic_report.md"
DOCX = REPO_ROOT / "docs/deliverables/SAMUEL KAOMA 2022016530 Final Report.docx"
PDF = REPO_ROOT / "docs/deliverables/SAMUEL KAOMA 2022016530 Final Report.pdf"

MAX_ROUNDS = 4

CONTENTS_HEADER = "| Section | Title | Page |"
TABLES_HEADER = "| Table | Title | Section | Page |"
FIGURES_HEADER = "| Figure | Title | Section | Page |"

# `wdExportFormatPDF`. Fields are updated first so the footer page numbers and
# anything else field-driven are current in the exported file.
EXPORT = """
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {{
  $doc = $word.Documents.Open('{docx}', $false, $true)
  $doc.Fields.Update() | Out-Null
  $doc.ExportAsFixedFormat('{pdf}', 17)
  $doc.Close(0)
}} finally {{
  $word.Quit()
}}
"""


def strip_emphasis(cell: str) -> str:
    return cell.replace("**", "").replace("`", "").strip()


def heading_key(section: str, title: str) -> str:
    """The text the heading is expected to start with in the rendered document."""
    if not section:
        return title
    if section.startswith("Appendix ") or len(section) == 1 and section.isalpha():
        # The appendix rows carry the full heading in their title cell already.
        return title
    return f"{section}. {title}" if "." not in section else f"{section} {title}"


def page_index(pages: list[str], key: str, exact: bool) -> int | None:
    """First page carrying `key` as a line of its own, or as a line prefix.

    Headings are matched exactly. A prefix match would find the contents list
    first, because a row there renders as the heading text followed by its page
    number. Captions are matched on the prefix, since the caption continues past
    the label.
    """
    wanted = re.sub(r"\s+", " ", key).casefold()
    for number, text in enumerate(pages, start=1):
        for line in text.split("\n"):
            candidate = re.sub(r"\s+", " ", line).strip().casefold()
            if candidate == wanted or (not exact and candidate.startswith(wanted)):
                return number
    return None


def read_pages(pdf_path: Path) -> list[str]:
    with pdfplumber.open(str(pdf_path)) as document:
        return [page.extract_text() or "" for page in document.pages]


def export_pdf(pdf_path: Path) -> None:
    script = EXPORT.format(docx=str(DOCX).replace("'", "''"), pdf=str(pdf_path).replace("'", "''"))
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        check=True,
        capture_output=True,
    )


def build_docx() -> None:
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/build_docx_deliverables.py"), "report"],
        check=True,
        cwd=REPO_ROOT,
        capture_output=True,
    )


def table_rows(lines: list[str], header: str) -> tuple[int, int]:
    """Index range of the data rows under `header`, separator row excluded."""
    start = lines.index(header) + 2
    end = start
    while end < len(lines) and lines[end].startswith("|"):
        end += 1
    return start, end


def collect_keys(lines: list[str]) -> list[tuple[int, str, bool]]:
    """Row index, lookup key and match mode for every entry in the three lists."""
    keys: list[tuple[int, str, bool]] = []

    start, end = table_rows(lines, CONTENTS_HEADER)
    for index in range(start, end):
        cells = [cell.strip() for cell in lines[index].strip("|").split("|")]
        keys.append((index, heading_key(strip_emphasis(cells[0]), strip_emphasis(cells[1])), True))

    for header, label in ((TABLES_HEADER, "Table"), (FIGURES_HEADER, "Figure")):
        start, end = table_rows(lines, header)
        for index in range(start, end):
            cells = [cell.strip() for cell in lines[index].strip("|").split("|")]
            keys.append((index, f"{label} {strip_emphasis(cells[0])}.", False))

    return keys


def write_pages(lines: list[str], resolved: dict[int, str]) -> list[str]:
    updated = list(lines)
    for index, page in resolved.items():
        cells = [cell.strip() for cell in updated[index].strip("|").split("|")]
        cells[-1] = page
        updated[index] = "| " + " | ".join(cells) + " |"
    return updated


def measure(pdf_path: Path, lines: list[str]) -> tuple[dict[int, str], list[str]]:
    pages = read_pages(pdf_path)
    resolved: dict[int, str] = {}
    missing: list[str] = []
    for index, key, exact in collect_keys(lines):
        found = page_index(pages, key, exact)
        if found is None:
            missing.append(key)
            resolved[index] = ""
        else:
            resolved[index] = str(found)
    return resolved, missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report staleness instead of writing")
    arguments = parser.parse_args()

    text = SOURCE.read_text(encoding="utf-8")
    for header in (CONTENTS_HEADER, TABLES_HEADER, FIGURES_HEADER):
        if header not in text:
            raise SystemExit(f"list header not found in {SOURCE.name}: {header}")

    original = text
    with tempfile.TemporaryDirectory() as workdir:
        probe = Path(workdir) / "probe.pdf"
        for round_number in range(1, MAX_ROUNDS + 1):
            build_docx()
            export_pdf(probe)
            lines = SOURCE.read_text(encoding="utf-8").split("\n")
            resolved, missing = measure(probe, lines)
            if missing:
                raise SystemExit("could not locate in the rendered document:\n  " + "\n  ".join(missing))

            updated = write_pages(lines, resolved)
            if updated == lines:
                print(f"page numbers stable after {round_number} round(s)")
                break
            if arguments.check:
                SOURCE.write_text(original, encoding="utf-8")
                print("page numbers are stale; run scripts/paginate_report.py")
                return 1
            SOURCE.write_text("\n".join(updated), encoding="utf-8")
        else:
            raise SystemExit(f"page numbers did not settle in {MAX_ROUNDS} rounds")

    build_docx()
    export_pdf(PDF)
    print(f"wrote {PDF.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
