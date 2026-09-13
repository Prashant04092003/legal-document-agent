from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.shared import Inches, Pt


DEFAULT_OUTPUT_PATH = Path("outputs/affidavit_in_reply.docx")


# ============================================================================
# GENERAL HELPERS
# ============================================================================

def _get_value(data: Any, *names: str, default: Any = None) -> Any:
    """Read a value from either a dictionary or an object."""
    for name in names:
        if isinstance(data, dict):
            value = data.get(name)
        else:
            value = getattr(data, name, None)

        if value not in (None, ""):
            return value

    return default


def _require(value: Any, field_name: str) -> Any:
    """Raise a useful error when a required rendering value is missing."""
    if value is None or value == "":
        raise ValueError(f"Missing required draft field: {field_name}")
    return value


def _set_run_font(run, *, bold: bool = False, size: int = 12) -> None:
    """Apply the document's standard font."""
    run.font.name = "Times New Roman"
    run.font.size = Pt(size)
    run.bold = bold


def _configure_document(document: Document) -> None:
    """Apply page and default paragraph settings."""
    section = document.sections[0]

    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

    style = document.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    paragraph_format = style.paragraph_format
    paragraph_format.space_after = Pt(6)
    paragraph_format.line_spacing = 1.15


def _add_paragraph(
    document: Document,
    text: str = "",
    *,
    alignment=WD_ALIGN_PARAGRAPH.LEFT,
    bold: bool = False,
    all_caps: bool = False,
    space_before: float = 0,
    space_after: float = 6,
    line_spacing: float = 1.15,
):
    """Add a standard formatted paragraph."""
    paragraph = document.add_paragraph()
    paragraph.alignment = alignment

    fmt = paragraph.paragraph_format
    fmt.space_before = Pt(space_before)
    fmt.space_after = Pt(space_after)
    fmt.line_spacing = line_spacing

    display_text = str(text)

    if all_caps:
        display_text = display_text.upper()

    run = paragraph.add_run(display_text)
    _set_run_font(run, bold=bold)

    return paragraph


def _add_numbered_body_paragraph(
    document: Document,
    number: int,
    text: str,
):
    """
    Add a numbered affidavit paragraph.

    Number is bold; substantive paragraph text is normal and justified.
    """
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    fmt = paragraph.paragraph_format
    fmt.space_before = Pt(3)
    fmt.space_after = Pt(8)
    fmt.line_spacing = 1.15

    number_run = paragraph.add_run(f"{number}. ")
    _set_run_font(number_run, bold=True)

    text_run = paragraph.add_run(str(text).strip())
    _set_run_font(text_run, bold=False)

    return paragraph


def _add_prayer_item(
    document: Document,
    letter: str,
    text: str,
):
    """Add a lettered prayer item with a bold letter."""
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    fmt = paragraph.paragraph_format
    fmt.left_indent = Inches(0.2)
    fmt.first_line_indent = Inches(-0.2)
    fmt.space_after = Pt(5)
    fmt.line_spacing = 1.15

    letter_run = paragraph.add_run(f"({letter}) ")
    _set_run_font(letter_run, bold=True)

    text_run = paragraph.add_run(str(text).strip())
    _set_run_font(text_run, bold=False)

    return paragraph


# ============================================================================
# LOW-LEVEL TABLE HELPERS
# ============================================================================

def _remove_table_borders(table) -> None:
    """Make a Word table visually borderless."""
    for row in table.rows:
        for cell in row.cells:
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_borders = tc_pr.first_child_found_in("w:tcBorders")

            if tc_borders is None:
                tc_borders = OxmlElement("w:tcBorders")
                tc_pr.append(tc_borders)

            for edge in (
                "top",
                "left",
                "bottom",
                "right",
                "insideH",
                "insideV",
            ):
                existing = tc_borders.find(
                    f"{{http://schemas.openxmlformats.org/wordprocessingml/2006/main}}{edge}"
                )

                if existing is None:
                    existing = OxmlElement(f"w:{edge}")
                    tc_borders.append(existing)

                existing.set(
                    "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val",
                    "nil",
                )


# ============================================================================
# CAUSE TITLE
# ============================================================================

def _parse_cause_title_string(cause_title: str) -> dict[str, Any]:
    """
    Convert the existing Phase 4 cause-title string into a structured
    renderer representation.

    Existing Phase 4 value:

        Petitioner vs. Respondent 1 and Respondent 2

    becomes:

        {
            "petitioner": {...},
            "respondents": [...]
        }

    No new party information is created.
    """
    text = " ".join(str(cause_title).split())

    if not text:
        return {
            "petitioner": None,
            "respondents": [],
        }

    # Split only on the existing "vs." separator.
    match = re.split(
        r"\s+vs\.?\s+",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )

    if len(match) != 2:
        return {
            "petitioner": {
                "name": text,
                "tag": "... Petitioner",
            },
            "respondents": [],
        }

    petitioner_text = match[0].strip()
    respondents_text = match[1].strip()

    # Existing Phase 4 joins two respondents using "and".
    # For more than two respondents, the existing comma structure is
    # also handled conservatively.
    respondent_names: list[str] = []

    if re.search(
        r"\s+and\s+",
        respondents_text,
        flags=re.IGNORECASE,
    ):
        parts = re.split(
            r"\s+and\s+",
            respondents_text,
            flags=re.IGNORECASE,
        )

        if len(parts) == 2:
            respondent_names = [
                parts[0].strip(),
                parts[1].strip(),
            ]
        else:
            respondent_names = [
                part.strip()
                for part in parts
                if part.strip()
            ]
    else:
        respondent_names = [
            part.strip()
            for part in respondents_text.split(",")
            if part.strip()
        ]

    respondents = []

    for index, name in enumerate(respondent_names, start=1):
        respondents.append(
            {
                "name": name,
                "tag": f"... Respondent No. {index}",
            }
        )

    return {
        "petitioner": {
            "name": petitioner_text,
            "tag": "... Petitioner",
        },
        "respondents": respondents,
    }


def _add_party_row(
    document: Document,
    party_text: str,
    tag: str,
    *,
    prefix: str = "",
) -> None:
    """Render one cause-title party row."""
    table = document.add_table(rows=1, cols=2)
    table.autofit = False

    table.columns[0].width = Inches(5.2)
    table.columns[1].width = Inches(1.8)

    row = table.rows[0]

    left_cell = row.cells[0]
    right_cell = row.cells[1]

    left_cell.width = Inches(5.2)
    right_cell.width = Inches(1.8)

    left_cell.vertical_alignment = (
        WD_CELL_VERTICAL_ALIGNMENT.CENTER
    )
    right_cell.vertical_alignment = (
        WD_CELL_VERTICAL_ALIGNMENT.CENTER
    )

    left_paragraph = left_cell.paragraphs[0]
    left_paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    left_paragraph.paragraph_format.space_after = Pt(2)

    left_run = left_paragraph.add_run(
        f"{prefix}{party_text}".strip()
    )
    _set_run_font(left_run)

    right_paragraph = right_cell.paragraphs[0]
    right_paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    right_paragraph.paragraph_format.space_after = Pt(2)

    right_run = right_paragraph.add_run(tag)
    _set_run_font(right_run)

    _remove_table_borders(table)


def _add_cause_title(
    document: Document,
    cause_title: Any,
) -> None:
    """
    Render the cause title in reference-style party layout.

    Supports:
    - structured cause-title dictionaries
    - lists
    - existing Phase 4 string representation
    """
    if isinstance(cause_title, dict):
        structured = cause_title

    elif isinstance(cause_title, list):
        for item in cause_title:
            _add_paragraph(
                document,
                str(item),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                space_after=3,
            )
        return

    else:
        structured = _parse_cause_title_string(
            str(cause_title)
        )

    petitioner = structured.get("petitioner")
    respondents = structured.get("respondents", [])

    if isinstance(petitioner, dict):
        petitioner_name = petitioner.get("name", "")
        petitioner_tag = (
            petitioner.get("tag")
            or "... Petitioner"
        )
    else:
        petitioner_name = str(petitioner or "")
        petitioner_tag = "... Petitioner"

    if petitioner_name:
        _add_party_row(
            document,
            petitioner_name,
            petitioner_tag,
        )

    _add_paragraph(
        document,
        "VERSUS",
        alignment=WD_ALIGN_PARAGRAPH.CENTER,
        bold=False,
        all_caps=True,
        space_before=2,
        space_after=6,
    )

    for index, respondent in enumerate(
        respondents,
        start=1,
    ):
        if isinstance(respondent, dict):
            name = respondent.get("name", "")
            tag = respondent.get("tag") or (
                f"... Respondent No. {index}"
            )
            prefix = respondent.get("prefix", "")
        else:
            name = str(respondent)
            tag = f"... Respondent No. {index}"
            prefix = ""

        if name:
            _add_party_row(
                document,
                name,
                tag,
                prefix=prefix,
            )


# ============================================================================
# DEPONENT CLAUSE
# ============================================================================

def _normalize_deponent_clause(clause: Any) -> str:
    """
    Convert the existing Phase 4 deponent identity string into the
    reference-style affidavit opening clause.

    Existing value:

        Arvind Rajan, Deputy Metropolitan Commissioner,
        Mumbai Metropolitan Region Development Authority,
        Bandra East, Mumbai, Maharashtra, Respondent No. 2

    Rendered as:

        I, Arvind Rajan, Deputy Metropolitan Commissioner,
        Mumbai Metropolitan Region Development Authority,
        Bandra East, Mumbai, Maharashtra, Respondent No. 2,
        do hereby solemnly affirm and state as under:
    """
    text = " ".join(str(clause).split())

    if not text:
        return ""

    # Already normalized.
    if re.search(
        r"\bdo hereby solemnly affirm and state as under\b",
        text,
        flags=re.IGNORECASE,
    ):
        if not text.startswith("I,"):
            text = "I, " + text

        if not text.endswith(":"):
            text += ":"

        return text

    # Avoid accidentally adding "I," twice.
    if text.startswith("I, "):
        identity = text[3:].strip()
    else:
        identity = text

    return (
        f"I, {identity}, "
        "do hereby solemnly affirm and state as under:"
    )


# ============================================================================
# DATE NORMALIZATION
# ============================================================================

def _ordinal_day(day: int) -> str:
    """Return an English ordinal day suffix."""
    if 10 <= day % 100 <= 20:
        suffix = "th"
    else:
        suffix = {
            1: "st",
            2: "nd",
            3: "rd",
        }.get(day % 10, "th")

    return f"{day}{suffix}"


def _format_affidavit_date(date_value: Any) -> str:
    """
    Convert common extracted date formats into the reference-style
    '5th day of September 2026'.

    If parsing is not possible, preserve the original value.
    """
    text = str(date_value or "").strip()

    if not text:
        return ""

    # Already in desired form.
    if re.search(
        r"\b\d{1,2}(st|nd|rd|th)\s+day\s+of\b",
        text,
        flags=re.IGNORECASE,
    ):
        return text

    patterns = (
        r"^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$",
        r"^(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})$",
    )

    for pattern in patterns:
        match = re.match(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            day = int(match.group(1))
            month = match.group(2)
            year = match.group(3)

            return (
                f"{_ordinal_day(day)} day of "
                f"{month} {year}"
            )

    return text


# ============================================================================
# JURAT
# ============================================================================

def _normalize_jurat(jurat: Any) -> dict[str, str]:
    """
    Convert the existing Phase 4 jurat string into structured rendering
    values.
    """
    if isinstance(jurat, dict):
        affirmed = str(
            jurat.get("affirmed", "")
        ).strip()

        date_line = str(
            jurat.get("date", "")
        ).strip()

        before_me = str(
            jurat.get("before_me", "Before Me")
        ).strip()

        return {
            "affirmed": affirmed,
            "date": date_line,
            "before_me": before_me or "Before Me",
        }

    lines = [
        line.strip()
        for line in str(jurat).splitlines()
    ]

    lines = [
        line
        for line in lines
        if line
    ]

    affirmed = lines[0] if lines else ""
    date_line = lines[1] if len(lines) > 1 else ""

    return {
        "affirmed": affirmed,
        "date": date_line,
        "before_me": "Before Me",
    }


def _add_jurat(
    document: Document,
    jurat: Any,
) -> None:
    """Render the jurat with reference-style attestation layout."""
    normalized = _normalize_jurat(jurat)

    affirmed = normalized["affirmed"]
    date_line = normalized["date"]
    before_me = normalized["before_me"]

    if affirmed:
        _add_paragraph(
            document,
            affirmed,
            alignment=WD_ALIGN_PARAGRAPH.LEFT,
            space_before=8,
            space_after=2,
        )

    if date_line:
        # Existing Phase 4 supplies:
        # "On this 5 September 2026"
        #
        # Renderer changes only the date presentation.
        match = re.match(
            r"^(On\s+this\s+)(.+)$",
            date_line,
            flags=re.IGNORECASE,
        )

        if match:
            date_part = _format_affidavit_date(
                match.group(2)
            )

            rendered_date = (
                match.group(1)
                + date_part
            )
        else:
            rendered_date = date_line

        _add_paragraph(
            document,
            rendered_date,
            alignment=WD_ALIGN_PARAGRAPH.LEFT,
            space_after=12,
        )

    # Before Me left / DEPONENT right.
    table = document.add_table(rows=1, cols=2)
    table.autofit = False

    table.columns[0].width = Inches(4)
    table.columns[1].width = Inches(3)

    left_cell = table.cell(0, 0)
    right_cell = table.cell(0, 1)

    left_cell.width = Inches(4)
    right_cell.width = Inches(3)

    left_paragraph = left_cell.paragraphs[0]
    left_paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    left_paragraph.paragraph_format.space_after = Pt(2)

    left_run = left_paragraph.add_run(before_me)
    _set_run_font(left_run)

    right_paragraph = right_cell.paragraphs[0]
    right_paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    right_paragraph.paragraph_format.space_after = Pt(2)

    right_run = right_paragraph.add_run("DEPONENT")
    _set_run_font(right_run)

    _remove_table_borders(table)


# ============================================================================
# VERIFICATION
# ============================================================================

def _add_verification(
    document: Document,
    verification: Any,
) -> None:
    """
    Render verification.

    The Phase 4 builder currently includes the word VERIFICATION in
    its string. The renderer owns the heading, so that duplicate is
    stripped here.
    """
    _add_paragraph(
        document,
        "VERIFICATION",
        alignment=WD_ALIGN_PARAGRAPH.CENTER,
        bold=True,
        all_caps=True,
        space_before=12,
        space_after=10,
    )

    if isinstance(verification, dict):
        body = str(
            verification.get("body", "")
        ).strip()

        verified_at = str(
            verification.get("verified_at", "")
        ).strip()

        deponent = str(
            verification.get(
                "deponent",
                "DEPONENT",
            )
        ).strip()

        if body:
            _add_paragraph(
                document,
                body,
                alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
                space_after=10,
            )

        if verified_at:
            _add_paragraph(
                document,
                verified_at,
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                space_after=12,
            )

        _add_paragraph(
            document,
            deponent or "DEPONENT",
            alignment=WD_ALIGN_PARAGRAPH.RIGHT,
            all_caps=True,
            space_after=4,
        )

        return

    lines = [
        line.strip()
        for line in str(verification).splitlines()
        if line.strip()
    ]

    # Remove the heading supplied by Phase 4 because this renderer
    # already adds it.
    filtered_lines = []

    for line in lines:
        if line.upper() == "VERIFICATION":
            continue

        filtered_lines.append(line)

    for line in filtered_lines:
        if line.upper() == "DEPONENT":
            _add_paragraph(
                document,
                "DEPONENT",
                alignment=WD_ALIGN_PARAGRAPH.RIGHT,
                all_caps=True,
                space_after=4,
            )
        else:
            # The "Verified at ..." line is better treated as an
            # attestation line rather than body text.
            if line.lower().startswith("verified at "):
                alignment = WD_ALIGN_PARAGRAPH.LEFT
                space_after = 12
            else:
                alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                space_after = 6

            _add_paragraph(
                document,
                line,
                alignment=alignment,
                space_after=space_after,
            )


# ============================================================================
# ADVOCATE BLOCK
# ============================================================================

def _normalize_advocate(advocate: Any) -> list[str]:
    """
    Normalize the existing Phase 4 advocate representation.

    Existing Phase 4 value:

        Rajan & Associates; Respondent No. 2

    becomes:

        [
            "Rajan & Associates",
            "Respondent No. 2"
        ]
    """
    if isinstance(advocate, dict):
        firm = (
            advocate.get("firm")
            or advocate.get("name")
            or ""
        )

        acting_for = (
            advocate.get("acting_for")
            or advocate.get("role")
            or ""
        )

        return [
            str(value).strip()
            for value in (firm, acting_for)
            if str(value).strip()
        ]

    if isinstance(advocate, list):
        return [
            str(value).strip()
            for value in advocate
            if str(value).strip()
        ]

    text = str(advocate).strip()

    if not text:
        return []

    # Existing builder uses "; " as separator.
    if ";" in text:
        return [
            part.strip()
            for part in text.split(";")
            if part.strip()
        ]

    return [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]


def _add_advocate_block(
    document: Document,
    advocate: Any,
) -> None:
    """Render advocate/drafting block in separate lines."""
    lines = _normalize_advocate(advocate)

    if not lines:
        return

    for index, line in enumerate(lines):
        _add_paragraph(
            document,
            line,
            alignment=WD_ALIGN_PARAGRAPH.LEFT,
            bold=index == 0,
            all_caps=index == 0,
            space_before=2 if index == 0 else 0,
            space_after=3,
        )


# ============================================================================
# EXHIBIT
# ============================================================================

def _add_exhibit(
    document: Document,
    exhibit: Any,
) -> None:
    """Render the exhibit reference when present."""
    if not exhibit:
        return

    if isinstance(exhibit, dict):
        text = (
            exhibit.get("label")
            or exhibit.get("reference")
            or exhibit.get("text")
            or ""
        )
    else:
        text = str(exhibit)

    if not text:
        return

    _add_paragraph(
        document,
        text,
        alignment=WD_ALIGN_PARAGRAPH.CENTER,
        bold=True,
        space_before=6,
        space_after=8,
    )


# ============================================================================
# PRAYER
# ============================================================================

def _add_prayer(
    document: Document,
    prayer: Any,
) -> None:
    """
    Render the prayer without changing its substantive content.

    If Phase 4 supplies a single prayer string, it is presented as one
    lettered prayer item. This improves fidelity to the reference's
    lettered prayer structure without inventing additional reliefs.
    """
    if not prayer:
        return

    _add_paragraph(
        document,
        "PRAYER",
        alignment=WD_ALIGN_PARAGRAPH.CENTER,
        bold=True,
        all_caps=True,
        space_before=8,
        space_after=8,
    )

    if isinstance(prayer, dict):
        opening = str(
            prayer.get("opening", "")
        ).strip()

        items = prayer.get("items", [])

        if opening:
            _add_paragraph(
                document,
                opening,
                alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
                space_after=6,
            )

        for index, item in enumerate(items):
            if isinstance(item, dict):
                letter = item.get(
                    "letter",
                    chr(ord("a") + index),
                )

                text = (
                    item.get("text")
                    or item.get("content")
                    or ""
                )
            else:
                letter = chr(ord("a") + index)
                text = str(item)

            if text:
                _add_prayer_item(
                    document,
                    str(letter),
                    str(text),
                )

        return

    if isinstance(prayer, list):
        for index, item in enumerate(prayer):
            if str(item).strip():
                _add_prayer_item(
                    document,
                    chr(ord("a") + index),
                    str(item),
                )

        return

    prayer_lines = [
        line.strip()
        for line in str(prayer).splitlines()
        if line.strip()
    ]

    if not prayer_lines:
        return

    # Existing generated draft has one substantive prayer sentence.
    #
    # We do NOT invent b/c clauses. We simply place the existing prayer
    # into the reference-style "(a)" structure.
    if len(prayer_lines) == 1:
        _add_prayer_item(
            document,
            "a",
            prayer_lines[0],
        )
        return

    for index, line in enumerate(prayer_lines):
        _add_prayer_item(
            document,
            chr(ord("a") + index),
            line,
        )


# ============================================================================
# DRAFT VALIDATION
# ============================================================================

def validate_generated_draft(
    generated_draft: dict[str, Any],
) -> None:
    """
    Validate that the Phase 4 generated draft contains enough structure
    for document rendering.

    This is renderer-input validation only and does not replace the
    Phase 5 deterministic validator.
    """
    if not isinstance(generated_draft, dict):
        raise TypeError(
            "generated_draft must be a dictionary"
        )

    required_sections = (
        "FORUM_HEADING",
        "JURISDICTION",
        "CASE_NUMBER",
        "CAUSE_TITLE",
        "AFFIDAVIT_TITLE",
        "DEPONENT_CLAUSE",
    )

    sections = generated_draft.get("sections")

    if not isinstance(sections, dict):
        raise ValueError(
            "generated_draft['sections'] must be a dictionary"
        )

    for section_name in required_sections:
        value = sections.get(section_name)

        if value is None or value == "":
            raise ValueError(
                "Missing required generated draft section: "
                + section_name
            )

    paragraphs = generated_draft.get("paragraphs")

    if not isinstance(paragraphs, list):
        raise ValueError(
            "generated_draft['paragraphs'] must be a list"
        )

    if not paragraphs:
        raise ValueError(
            "generated_draft must contain at least one body paragraph"
        )

    for index, paragraph in enumerate(
        paragraphs,
        start=1,
    ):
        if isinstance(paragraph, dict):
            text = (
                paragraph.get("text")
                or paragraph.get("content")
                or paragraph.get("paragraph")
            )
        else:
            text = paragraph

        if text is None or not str(text).strip():
            raise ValueError(
                f"Generated draft paragraph {index} has no content"
            )


# ============================================================================
# MAIN DOCX RENDERER
# ============================================================================

def render_affidavit_docx(
    generated_draft: dict[str, Any],
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    """
    Render the existing Phase 4 generated draft into a DOCX.

    IMPORTANT:
    - Does not modify generated_draft.
    - Does not call an LLM.
    - Does not generate new substantive legal content.
    - Performs only deterministic presentation/normalization.
    """
    validate_generated_draft(generated_draft)

    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    document = Document()
    _configure_document(document)

    sections = generated_draft["sections"]

    # ------------------------------------------------------------------
    # 1. FORUM HEADING
    # ------------------------------------------------------------------
    _add_paragraph(
        document,
        _require(
            sections["FORUM_HEADING"],
            "FORUM_HEADING",
        ),
        alignment=WD_ALIGN_PARAGRAPH.CENTER,
        bold=True,
        all_caps=True,
        space_after=2,
    )

    # ------------------------------------------------------------------
    # 2. JURISDICTION
    # ------------------------------------------------------------------
    _add_paragraph(
        document,
        _require(
            sections["JURISDICTION"],
            "JURISDICTION",
        ),
        alignment=WD_ALIGN_PARAGRAPH.CENTER,
        bold=True,
        all_caps=True,
        space_after=2,
    )

    # ------------------------------------------------------------------
    # 3. CASE NUMBER
    # ------------------------------------------------------------------
    _add_paragraph(
        document,
        _require(
            sections["CASE_NUMBER"],
            "CASE_NUMBER",
        ),
        alignment=WD_ALIGN_PARAGRAPH.CENTER,
        bold=True,
        all_caps=True,
        space_after=10,
    )

    # ------------------------------------------------------------------
    # 4. CAUSE TITLE
    # ------------------------------------------------------------------
    _add_cause_title(
        document,
        _require(
            sections["CAUSE_TITLE"],
            "CAUSE_TITLE",
        ),
    )

    # ------------------------------------------------------------------
    # 5. AFFIDAVIT TITLE
    # ------------------------------------------------------------------
    _add_paragraph(
        document,
        _require(
            sections["AFFIDAVIT_TITLE"],
            "AFFIDAVIT_TITLE",
        ),
        alignment=WD_ALIGN_PARAGRAPH.CENTER,
        bold=True,
        all_caps=True,
        space_before=8,
        space_after=12,
    )

    # ------------------------------------------------------------------
    # 6. DEPONENT CLAUSE
    # ------------------------------------------------------------------
    normalized_deponent = _normalize_deponent_clause(
        _require(
            sections["DEPONENT_CLAUSE"],
            "DEPONENT_CLAUSE",
        )
    )

    _add_paragraph(
        document,
        normalized_deponent,
        alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
        space_after=12,
    )

    # ------------------------------------------------------------------
    # 7. NUMBERED BODY PARAGRAPHS
    # ------------------------------------------------------------------
    paragraphs = generated_draft["paragraphs"]

    for index, paragraph in enumerate(
        paragraphs,
        start=1,
    ):
        if isinstance(paragraph, dict):
            text = (
                paragraph.get("text")
                or paragraph.get("content")
                or paragraph.get("paragraph")
            )
        else:
            text = paragraph

        _add_numbered_body_paragraph(
            document,
            index,
            str(text).strip(),
        )

    # ------------------------------------------------------------------
    # EXHIBIT
    # ------------------------------------------------------------------
    _add_exhibit(
        document,
        generated_draft.get("exhibit"),
    )

    # ------------------------------------------------------------------
    # 8. PRAYER
    # ------------------------------------------------------------------
    _add_prayer(
        document,
        generated_draft.get("prayer"),
    )

    # ------------------------------------------------------------------
    # 9. JURAT
    # ------------------------------------------------------------------
    if generated_draft.get("jurat"):
        _add_jurat(
            document,
            generated_draft["jurat"],
        )

    # ------------------------------------------------------------------
    # 10. VERIFICATION
    # ------------------------------------------------------------------
    if generated_draft.get("verification"):
        _add_verification(
            document,
            generated_draft["verification"],
        )

    # ------------------------------------------------------------------
    # ADVOCATE / DRAFTING BLOCK
    # ------------------------------------------------------------------
    _add_advocate_block(
        document,
        generated_draft.get("advocate"),
    )

    document.save(output_path)

    return output_path