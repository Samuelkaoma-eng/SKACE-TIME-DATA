"""Rebuild the Word deliverables from their markdown sources.

Each deliverable keeps the cover page of the document it replaces: the cover
paragraphs are copied verbatim from the existing .docx, and only the body is
re-rendered from markdown by pandoc using that same .docx as the style
reference. This keeps the University cover block and the document styles stable
across rebuilds while the content tracks the markdown source.

Usage:

    python scripts/build_docx_deliverables.py                 # rebuild all
    python scripts/build_docx_deliverables.py report          # rebuild one

Requires pandoc on PATH and python-docx.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from xml.etree import ElementTree
from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt, Twips
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn as _qn
from docx.oxml import OxmlElement

REPO_ROOT = Path(__file__).resolve().parents[1]

CAPTION_PATTERN = re.compile(r"^(Table|Figure) [A-D]?\d+\.")
SIGNATURE_PATH = REPO_ROOT / "docs/deliverables/assets/signature.jpg"

# A heading no longer than this is given room to sit on a single line; a value
# no longer than this is never allowed to break across lines.
HEADING_ON_ONE_LINE = 16
UNBREAKABLE_TOKEN = 16

# Width of the widest character in the body face, in twips, measured from a
# rendered PDF of this report, plus the left and right cell margins. Sizing to
# the widest character rather than the average is what stops a word being
# broken through the middle.
CHAR_TWIPS = 130
CELL_PADDING = 260
BODY_POINTS = 11
MIN_TABLE_POINTS = 8

# The cover block is copied from the previous build rather than rendered from
# markdown, so these lines are corrected on the way through.
COVER_SEARCH_DEPTH = 8
COVER_CORRECTIONS = {
    "SCHOOL OF NATURAL SCIENCE": "SCHOOL OF NATURAL AND APPLIED SCIENCES",
    "SCHOOL OF NATURAL SCIENCES": "SCHOOL OF NATURAL AND APPLIED SCIENCES",
    "DEPARTMENT OF COMPUTER SCIENCE": "DEPARTMENT OF COMPUTING AND INFORMATICS",
}

# The 2026 report template asks for these on the title page. They are written
# into paragraphs the cover already has, so the number of cover elements copied
# on the next rebuild does not change.
REPORT_COVER_TYPE = "FINAL YEAR PROJECT REPORT"
REPORT_COVER_YEAR = "Academic Year 2026"
REPORT_COVER_DEGREE = ("A report submitted in partial fulfilment of the requirements for the degree of "
                       "Bachelor of Science in Computer Science")
REPORT_COVER_DATE = ("21", "st", " October 2026")

# A4, in EMU, for printing. Margins are left as the reference document sets them.
A4_WIDTH = 7560310
A4_HEIGHT = 10692130


@dataclass(frozen=True)
class Deliverable:
    key: str
    source: str
    target: str
    body_start: str
    cover_children: int
    resource_path: str | None = None
    page_numbers: bool = False
    signature: bool = False
    report_cover: bool = False

    @property
    def source_path(self) -> Path:
        return REPO_ROOT / self.source

    @property
    def target_path(self) -> Path:
        return REPO_ROOT / self.target


DELIVERABLES = (
    Deliverable(
        key="report",
        source="report/final_academic_report.md",
        target="docs/deliverables/SAMUEL KAOMA 2022016530 Final Report.docx",
        body_start="## Declaration",
        cover_children=14,
        resource_path="report",
        page_numbers=True,
        signature=True,
        report_cover=True,
    ),
    Deliverable(
        key="validation",
        source="docs/validation_report.md",
        target="docs/deliverables/Validation_Report.docx",
        body_start="This document reports the validation results",
        cover_children=13,
        page_numbers=True,
    ),
    Deliverable(
        key="ai-log",
        source="docs/ai_usage_log.md",
        target="docs/deliverables/AI_Usage_Log.docx",
        body_start="# AI Usage Log",
        cover_children=0,
    ),
    Deliverable(
        key="tracker",
        source="docs/milestone_tracker.md",
        target="docs/deliverables/Milestone_Tracker.docx",
        body_start="# Milestone Tracker",
        cover_children=0,
    ),
    Deliverable(
        key="evidence",
        source="docs/evidence_index.md",
        target="docs/deliverables/Evidence_Index.docx",
        body_start="# Evidence Index",
        cover_children=0,
    ),
)


def body_markdown(deliverable: Deliverable) -> str:
    """Return the markdown from `body_start` onwards.

    Everything above it duplicates the cover page and is dropped so the rendered
    document does not repeat its own title block.
    """
    text = deliverable.source_path.read_text(encoding="utf-8")
    index = text.find(deliverable.body_start)
    if index < 0:
        raise SystemExit(f"body start marker not found in {deliverable.source}: {deliverable.body_start!r}")
    return text[index:]


def render(deliverable: Deliverable, workdir: Path) -> Path:
    reference = workdir / "reference.docx"
    shutil.copyfile(deliverable.target_path, reference)

    source = workdir / "body.md"
    source.write_text(body_markdown(deliverable), encoding="utf-8")

    rendered = workdir / "rendered.docx"
    command = [
        "pandoc",
        str(source),
        "--from=gfm",
        "--to=docx",
        # The cover page already carries the document title, so chapter headings
        # written as `##` in markdown render as Heading 1 in Word.
        "--shift-heading-level-by=-1",
        f"--reference-doc={reference}",
        f"--output={rendered}",
    ]
    if deliverable.resource_path:
        command.append(f"--resource-path={REPO_ROOT / deliverable.resource_path}")
    subprocess.run(command, check=True, cwd=REPO_ROOT)
    return rendered


def prepend_cover(deliverable: Deliverable, rendered: Path) -> None:
    """Copy the cover paragraphs of the existing document onto the new body."""
    if not deliverable.cover_children:
        shutil.copyfile(rendered, deliverable.target_path)
        return

    existing = Document(str(deliverable.target_path))
    fresh = Document(str(rendered))

    cover = list(existing.element.body)[: deliverable.cover_children]
    anchor = list(fresh.element.body)[0]
    for element in cover:
        anchor.addprevious(element)

    fresh.save(str(deliverable.target_path))


def prune_unused_media(path: Path) -> int:
    """Drop image parts the document does not reference.

    Pandoc carries the media of its reference document into the rendered file,
    so rebuilding a deliverable that already contains figures would embed each
    of them a second time and the file would grow on every rebuild. The cover
    logo and the figures actually referenced by the body are kept; everything
    else is removed along with its relationship entry.
    """
    relationships_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    document_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    office_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

    with zipfile.ZipFile(path) as archive:
        items = {info.filename: archive.read(info.filename) for info in archive.infolist()}
        order = [info.filename for info in archive.infolist()]

    used_ids: set[str] = set()
    for name, payload in items.items():
        if not name.endswith(".xml") or name.endswith(".rels"):
            continue
        root = ElementTree.fromstring(payload)
        for element in root.iter():
            for key, value in element.attrib.items():
                if key in (f"{{{office_ns}}}embed", f"{{{office_ns}}}link", f"{{{document_ns}}}embed"):
                    used_ids.add(value)

    kept_targets: set[str] = set()
    for name in list(items):
        if not name.endswith(".rels"):
            continue
        root = ElementTree.fromstring(items[name])
        changed = False
        for relationship in list(root):
            target = relationship.get("Target", "")
            if "media/" not in target:
                continue
            if relationship.get("Id") in used_ids:
                kept_targets.add(target.split("media/")[-1])
            else:
                root.remove(relationship)
                changed = True
        if changed:
            ElementTree.register_namespace("", relationships_ns)
            items[name] = ElementTree.tostring(root, encoding="UTF-8", xml_declaration=True)

    removed = 0
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in order:
            if name.startswith("word/media/") and name.split("/")[-1] not in kept_targets:
                removed += 1
                continue
            archive.writestr(name, items[name])
    return removed


# Eighths of a point. The outer rules are the weight a printed table needs to
# read as a table; the row separators are deliberately light so a forty-row
# appendix table stays legible without turning into a grid.
# Siblings that must follow `tblBorders` inside `tblPr`.
BORDERS_PRECEDE = ("shd", "tblLayout", "tblCellMar", "tblLook", "tblCaption", "tblDescription")

_OUTER_RULE = "8"
_ROW_RULE = "2"
_ROW_RULE_COLOUR = "BFBFBF"


def _border(tag: str, size: str, colour: str) -> OxmlElement:
    element = OxmlElement(f"w:{tag}")
    element.set(_qn("w:val"), "single")
    element.set(_qn("w:sz"), size)
    element.set(_qn("w:space"), "0")
    element.set(_qn("w:color"), colour)
    return element


def rule_tables(path: Path) -> None:
    """Give the `Table` style visible rules.

    Pandoc's table style carries a header underline of width zero, which is why
    every table renders as spaced text with no lines at all. Replace it with a
    rule above the header, below it and below the last row, plus a light
    separator between rows.
    """
    document = Document(str(path))
    style = document.styles["Table"].element

    table_properties = style.find(_qn("w:tblPr"))
    if table_properties is None:
        table_properties = OxmlElement("w:tblPr")
        style.insert(0, table_properties)

    for existing in table_properties.findall(_qn("w:tblBorders")):
        table_properties.remove(existing)

    borders = OxmlElement("w:tblBorders")
    borders.append(_border("top", _OUTER_RULE, "auto"))
    borders.append(_border("bottom", _OUTER_RULE, "auto"))
    borders.append(_border("insideH", _ROW_RULE, _ROW_RULE_COLOUR))
    # `tblBorders` has a fixed position among its siblings: after `tblInd`, before
    # `shd`, `tblLayout`, `tblCellMar` and `tblLook`. Word tolerates it out of
    # order when reading, then silently drops it the next time the document is
    # saved, so the rules would disappear as soon as anyone opened the file.
    anchor = next((child for child in table_properties
                   if child.tag.split("}")[1] in BORDERS_PRECEDE), None)
    if anchor is None:
        table_properties.append(borders)
    else:
        anchor.addprevious(borders)

    for conditional in style.findall(_qn("w:tblStylePr")):
        if conditional.get(_qn("w:type")) != "firstRow":
            continue
        cell_properties = conditional.find(_qn("w:tcPr"))
        if cell_properties is None:
            continue
        for existing in cell_properties.findall(_qn("w:tcBorders")):
            cell_properties.remove(existing)
        cell_borders = OxmlElement("w:tcBorders")
        cell_borders.append(_border("bottom", _OUTER_RULE, "auto"))
        cell_properties.insert(0, cell_borders)

    document.save(str(path))


def align_captions(path: Path) -> int:
    """Left-align table and figure captions and keep them with what they label.

    Body text is justified, which stretches the spacing of a caption that runs
    to several lines. Captions are set ragged right so the words keep their
    normal spacing, held on one page, and kept with the paragraph that follows,
    so a caption can neither split across a page break nor be left stranded at
    the foot of a page while its table starts on the next one.
    """
    document = Document(str(path))
    changed = 0
    for paragraph in document.paragraphs:
        text = paragraph.text.lstrip()
        if not CAPTION_PATTERN.match(text):
            continue
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        paragraph.paragraph_format.keep_together = True
        paragraph.paragraph_format.keep_with_next = True
        changed += 1
    document.save(str(path))
    return changed


def fit_tables(path: Path) -> int:
    """Size table columns to their contents.

    Pandoc gives every column the same width, so a table holding one long text
    column and several short numeric ones squeezes the numeric headings until
    they wrap mid-word. Width is shared out in proportion to the longest cell in
    each column, with a floor wide enough for the longest unbreakable word in
    the heading so a heading never wraps on its own account.
    """
    document = Document(str(path))
    section = document.sections[0]
    # A reference .docx need not carry explicit page geometry, in which case
    # python-docx reports None and Word falls back to its own defaults. Use the
    # geometry the other deliverables carry rather than failing the build.
    page_width = section.page_width if section.page_width is not None else 7772400
    left_margin = section.left_margin if section.left_margin is not None else 914400
    right_margin = section.right_margin if section.right_margin is not None else 914400
    available = int((page_width - left_margin - right_margin) / 635)

    adjusted = 0
    for table in document.tables:
        columns = len(table.columns)
        if not columns:
            continue

        longest = [0] * columns
        floors = [0] * columns
        for row_number, row in enumerate(table.rows):
            for index, cell in enumerate(row.cells[:columns]):
                text = cell.text.strip()
                longest[index] = max(longest[index], len(text))
                if not text:
                    continue
                if row_number == 0:
                    # Keep a short heading on one line rather than breaking it
                    # between its words.
                    floors[index] = max(floors[index], len(text) if len(text) <= HEADING_ON_ONE_LINE else 0)
                # A value such as -10.5664 must not be split; a long identifier
                # such as Q-10_first_to_last_interaction_duration may wrap.
                tokens = [len(part) for part in text.split() if len(part) <= UNBREAKABLE_TOKEN]
                floors[index] = max(floors[index], max(tokens, default=0))

        floor_widths = [max(word, 4) * CHAR_TWIPS + CELL_PADDING for word in floors]
        demanded = sum(floor_widths)

        shrink = 1.0
        if demanded > available:
            # The columns cannot all have the room their longest word needs. Give
            # each the same share of what it asked for and set the table in
            # smaller type, so the same words still fit on a line rather than
            # being broken through the middle.
            shrink = available / demanded
            floor_widths = [int(width * shrink) for width in floor_widths]

        weights = [max(value, 1) for value in longest]
        total = sum(weights)
        widths = [max(int(available * weight / total), floor) for weight, floor in zip(weights, floor_widths)]

        overflow = sum(widths) - available
        while overflow > 0:
            slack = [(widths[i] - floor_widths[i], i) for i in range(columns)]
            room, index = max(slack)
            if room <= 0:
                break
            take = min(room, overflow)
            widths[index] -= take
            overflow -= take

        # Cells inherit the justified body alignment, which in a narrow column
        # opens gaps between words wide enough to read as tab stops. Table text
        # is set ragged right instead.
        size = Pt(max(MIN_TABLE_POINTS, BODY_POINTS * shrink)) if shrink < 1 else None
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    if size is not None:
                        for run in paragraph.runs:
                            run.font.size = size

        grid = table._tbl.find(_qn("w:tblGrid"))
        if grid is None or len(grid) != columns:
            continue
        for column, width in zip(grid, widths):
            column.set(_qn("w:w"), str(width))
        for row in table.rows:
            for cell, width in zip(row.cells[:columns], widths):
                cell.width = Twips(width)
        adjusted += 1

    document.save(str(path))
    return adjusted


def correct_cover(path: Path) -> int:
    """Bring the cover block up to date with the current faculty names.

    The cover is carried over verbatim from the document being replaced, so a
    stale school or department name would survive every rebuild. Correcting it
    here fixes it once for every deliverable.
    """
    document = Document(str(path))
    changed = 0
    for paragraph in document.paragraphs[:COVER_SEARCH_DEPTH]:
        replacement = COVER_CORRECTIONS.get(paragraph.text.strip().upper())
        if replacement is None:
            continue
        for run in paragraph.runs[1:]:
            run._element.getparent().remove(run._element)
        paragraph.runs[0].text = replacement
        changed += 1
    if changed:
        document.save(str(path))
    return changed


def complete_report_cover(path: Path) -> int:
    """Give the report's title page the lines the 2026 template requires.

    The document type, the degree line, the academic year and the submission
    date are written into the title paragraph, the empty paragraph below it and
    the date line. Each is rewritten from the constants above on every build,
    so running the build twice leaves the cover as it was after the first run.
    """
    document = Document(str(path))
    cover = document.paragraphs[:14]
    changed = 0

    title_index = next((i for i, p in enumerate(cover) if p.style is not None and p.style.name == "Title"), None)
    if title_index is None:
        raise SystemExit("report cover has no Title paragraph")
    for run in cover[title_index].runs:
        if run.text.strip() in ("REPORT", REPORT_COVER_TYPE):
            # Assigning `run.text` would drop the line break that puts the
            # document type on a line of its own, so the run is rebuilt.
            run.text = ""
            run.add_break()
            run.add_text(REPORT_COVER_TYPE)
            changed += 1

    below = cover[title_index + 1]
    if below.text.strip() and not below.text.startswith(REPORT_COVER_DEGREE[:20]):
        raise SystemExit(f"expected an empty paragraph below the report title, found {below.text!r}")
    for run in list(below.runs):
        run._element.getparent().remove(run._element)
    below.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = below.add_run(REPORT_COVER_DEGREE)
    run.font.size = Pt(13)
    run.add_break()
    run = below.add_run(REPORT_COVER_YEAR)
    run.font.size = Pt(13)
    run.bold = True
    changed += 1

    date_line = next((p for p in cover if p.text.startswith("DATE:")), None)
    if date_line is None:
        raise SystemExit("report cover has no DATE line")
    runs = date_line.runs
    tab_run = next((i for i, r in enumerate(runs) if r._element.find(_qn("w:tab")) is not None), None)
    if tab_run is None:
        raise SystemExit("report cover DATE line has no tab")
    for run in runs[tab_run + 1:]:
        run._element.getparent().remove(run._element)
    day, suffix, rest = REPORT_COVER_DATE
    for text, superscript in ((day, False), (suffix, True), (rest, False)):
        run = date_line.add_run(text)
        run.font.size = Pt(14)
        run.font.superscript = superscript
    changed += 1

    document.save(str(path))
    return changed


def set_a4(path: Path) -> None:
    """Set every section to A4, which is what the department prints on."""
    document = Document(str(path))
    for section in document.sections:
        section.page_width = A4_WIDTH
        section.page_height = A4_HEIGHT
    document.save(str(path))


def sign(path: Path) -> bool:
    """Place the handwritten signature on the declaration line.

    The declaration is re-rendered from markdown on every build, so a signature
    inserted by hand in Word is lost each time. The image is kept at
    `docs/deliverables/assets/signature.jpg`, which is deliberately outside
    version control: the repository is public and a handwritten signature does
    not belong in it. A build without that file leaves the dotted rule as it is.
    """
    if not SIGNATURE_PATH.exists():
        return False

    document = Document(str(path))
    for paragraph in document.paragraphs:
        if not paragraph.text.startswith("Signed:"):
            continue
        remainder = paragraph.text.split("Date:", 1)
        tail = f"    Date: {remainder[1].strip()}" if len(remainder) > 1 else ""
        for run in list(paragraph.runs):
            run._element.getparent().remove(run._element)
        paragraph.add_run("Signed: ")
        paragraph.add_run().add_picture(str(SIGNATURE_PATH), width=Inches(1.58))
        if tail:
            paragraph.add_run(tail)
        document.save(str(path))
        return True
    return False


def add_page_numbers(path: Path) -> None:
    """Put a centred `PAGE` field in the footer of every section."""
    document = Document(str(path))
    namespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

    for section in document.sections:
        section.footer.is_linked_to_previous = False
        footer = section.footer
        paragraph = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        for run in list(paragraph.runs):
            run._element.getparent().remove(run._element)
        paragraph.alignment = 1  # centred

        run = paragraph.add_run()
        for tag, attributes, text in (
            ("fldChar", {"fldCharType": "begin"}, None),
            ("instrText", {"space": "preserve"}, " PAGE "),
            ("fldChar", {"fldCharType": "end"}, None),
        ):
            element = OxmlElement(f"w:{tag}")
            for key, value in attributes.items():
                prefix = "xml" if key == "space" else "w"
                uri = "http://www.w3.org/XML/1998/namespace" if key == "space" else namespace
                element.set(f"{{{uri}}}{key}", value)
            if text is not None:
                element.text = text
            run._element.append(element)

    document.save(str(path))


def build(deliverable: Deliverable) -> None:
    if not deliverable.target_path.exists():
        raise SystemExit(f"target does not exist, cannot reuse its cover and styles: {deliverable.target}")
    with tempfile.TemporaryDirectory() as raw:
        rendered = render(deliverable, Path(raw))
        prepend_cover(deliverable, rendered)
    cover = correct_cover(deliverable.target_path)
    if deliverable.report_cover:
        cover += complete_report_cover(deliverable.target_path)
    set_a4(deliverable.target_path)
    rule_tables(deliverable.target_path)
    fitted = fit_tables(deliverable.target_path)
    captions = align_captions(deliverable.target_path)
    signed = sign(deliverable.target_path) if deliverable.signature else False
    if deliverable.page_numbers:
        add_page_numbers(deliverable.target_path)
    removed = prune_unused_media(deliverable.target_path)
    size = deliverable.target_path.stat().st_size
    note = f", {removed} unused image part(s) pruned" if removed else ""
    mark = ", signed" if signed else (", UNSIGNED" if deliverable.signature else "")
    mark += f", {cover} cover line(s) corrected" if cover else ""
    print(f"wrote {deliverable.target} ({size:,} bytes, {fitted} table(s) fitted, {captions} caption(s) aligned{mark}{note})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "keys",
        nargs="*",
        choices=[item.key for item in DELIVERABLES] + [[]],
        help="deliverables to rebuild; default is all of them",
    )
    args = parser.parse_args()
    selected = args.keys or [item.key for item in DELIVERABLES]
    for deliverable in DELIVERABLES:
        if deliverable.key in selected:
            build(deliverable)
    return 0


if __name__ == "__main__":
    sys.exit(main())
