from __future__ import annotations

import re

from src.extraction.case_schema import CaseData, ReplyPoint


# ============================================================================
# TEXT NORMALIZATION
# ============================================================================

def _normalize_text(pages: list[str]) -> str:
    """
    Combine page-level text from Phase 1 and remove PDF extraction noise.

    Phase 1 is responsible for reading the PDF.
    This module only processes the extracted text.
    """
    if not pages:
        raise ValueError("No case-information pages were supplied.")

    text = "\n".join(pages)

    # Remove zero-width characters introduced by PDF extraction.
    text = text.replace("\u200b", "")

    # Normalize line endings.
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    return text


def _clean_line(line: str) -> str:
    """Normalize whitespace without changing substantive content."""
    return " ".join(line.strip().split())


# ============================================================================
# SECTION SPLITTING
# ============================================================================

_SECTION_MARKERS = [
    ("court_case_details", "1. Court and Case Details"),
    ("deponent_details", "2. Deponent Details"),
    ("reply_points", "3. Reply Points to be Incorporated"),
    ("prayer", "4. Prayer"),
    ("attestation", "5. Attestation Details"),
    ("advocate", "6. Advocate"),
]


def _split_sections(text: str) -> dict[str, str]:
    """
    Split the case-information document using its explicit section headings.
    """
    positions: list[tuple[str, str, int]] = []

    for key, marker in _SECTION_MARKERS:
        position = text.find(marker)

        if position == -1:
            raise ValueError(
                f"Required section not found: {marker}"
            )

        positions.append((key, marker, position))

    # Ensure the sections occur in the expected order.
    for previous, current in zip(positions, positions[1:]):
        if previous[2] >= current[2]:
            raise ValueError(
                "Case-information sections are missing or out of order."
            )

    sections: dict[str, str] = {}

    for index, (key, _marker, start) in enumerate(positions):
        if index + 1 < len(positions):
            end = positions[index + 1][2]
        else:
            end = len(text)

        sections[key] = text[start:end].strip()

    return sections


# ============================================================================
# GENERIC LABEL / VALUE EXTRACTION
# ============================================================================

def _extract_labelled_fields(
    section: str,
    *,
    heading: str,
    known_fields: set[str],
) -> dict[str, str]:
    """
    Extract structured Field -> Value pairs.

    Expected structure:

        Field
        Value
        Field
        Value

    A value is allowed to have the same text as another field name.

    Example:

        Filed on behalf of
        Respondent No. 2

    is valid even though "Respondent No. 2" is also a field label.
    """
    lines = [
        _clean_line(line)
        for line in section.splitlines()
        if _clean_line(line)
    ]

    if not lines:
        raise ValueError(f"Empty section: {heading}")

    if lines[0] != heading:
        raise ValueError(
            f"Expected section heading {heading!r}, got {lines[0]!r}"
        )

    fields: dict[str, str] = {}

    index = 1

    while index < len(lines):
        field = lines[index]

        if field not in known_fields:
            raise ValueError(
                f"Unexpected field in {heading!r}: {field!r}"
            )

        if field in fields:
            raise ValueError(
                f"Duplicate field in {heading!r}: {field!r}"
            )

        if index + 1 >= len(lines):
            raise ValueError(
                f"Missing value for field {field!r} in {heading!r}"
            )

        value = lines[index + 1]

        if not value:
            raise ValueError(
                f"Empty value for field {field!r} in {heading!r}"
            )

        fields[field] = value
        index += 2

    missing = known_fields - set(fields)

    if missing:
        raise ValueError(
            f"Missing fields in {heading!r}: {sorted(missing)}"
        )

    return fields


# ============================================================================
# SECTION 1 — COURT AND CASE DETAILS
# ============================================================================

def _extract_court_case_details(
    section: str,
) -> dict[str, str]:
    known_fields = {
        "Document Type",
        "Court",
        "Jurisdiction",
        "Proceeding Type",
        "Case Number",
        "Year",
        "Petitioner",
        "Respondent No. 1",
        "Respondent No. 2",
        "Filed on behalf of",
    }

    return _extract_labelled_fields(
        section,
        heading="1. Court and Case Details",
        known_fields=known_fields,
    )


def _populate_court_case_data(
    case_data: CaseData,
    fields: dict[str, str],
) -> None:
    case_data.document_type = fields["Document Type"]
    case_data.court = fields["Court"]
    case_data.jurisdiction = fields["Jurisdiction"]
    case_data.proceeding_type = fields["Proceeding Type"]
    case_data.case_number = fields["Case Number"]
    case_data.year = fields["Year"]
    case_data.petitioner = fields["Petitioner"]
    case_data.filed_on_behalf_of = fields["Filed on behalf of"]

    respondents: dict[str, str] = {}

    for field, value in fields.items():
        match = re.fullmatch(
            r"Respondent No\. (\d+)",
            field,
        )

        if match:
            respondent_number = match.group(1)
            respondents[respondent_number] = value

    if not respondents:
        raise ValueError("No respondents were extracted.")

    case_data.respondents = respondents


# ============================================================================
# SECTION 2 — DEPONENT DETAILS
# ============================================================================

def _extract_deponent_details(
    section: str,
) -> dict[str, str]:
    known_fields = {
        "Name",
        "Designation",
        "Organisation",
        "Address",
        "Verification verb",
    }

    return _extract_labelled_fields(
        section,
        heading="2. Deponent Details",
        known_fields=known_fields,
    )


def _populate_deponent_data(
    case_data: CaseData,
    fields: dict[str, str],
) -> None:
    case_data.deponent_name = fields["Name"]
    case_data.designation = fields["Designation"]
    case_data.organisation = fields["Organisation"]
    case_data.address = fields["Address"]
    case_data.verification_verb = fields["Verification verb"]


# ============================================================================
# SECTION 3 — REPLY POINTS
# ============================================================================

_POINT_PATTERN = re.compile(
    r"^Point\s+(\d+)\s+[—–-]\s+(.+)$"
)


def _extract_reply_points(
    section: str,
) -> list[ReplyPoint]:
    """
    Extract numbered reply points.

    The parser distinguishes between:

        Point heading
        Bullet
        Wrapped continuation of a bullet

    This is necessary because PDF extraction preserves physical line
    wrapping rather than logical sentence boundaries.
    """
    raw_lines = [
        _clean_line(line)
        for line in section.splitlines()
        if _clean_line(line)
    ]

    if not raw_lines:
        raise ValueError(
            "Reply-points section is empty."
        )

    if raw_lines[0] != "3. Reply Points to be Incorporated":
        raise ValueError(
            "Unexpected reply-points section heading."
        )

    # ------------------------------------------------------------------
    # Remove introductory instruction.
    # ------------------------------------------------------------------

    body_lines: list[str] = []

    skipping_instruction = False

    instruction_prefix = (
        "The following points are to be set out as numbered paragraphs"
    )

    for line in raw_lines[1:]:

        if line.startswith(instruction_prefix):
            skipping_instruction = True
            continue

        if skipping_instruction:

            if line == "and style of the reference affidavit.":
                skipping_instruction = False
                continue

            # Safety: if Point 1 starts before the expected continuation,
            # process it normally.
            if _POINT_PATTERN.match(line):
                skipping_instruction = False
                body_lines.append(line)

            continue

        body_lines.append(line)

    # ------------------------------------------------------------------
    # Parse logical points and bullets.
    # ------------------------------------------------------------------

    reply_points: list[ReplyPoint] = []

    current_point: ReplyPoint | None = None
    current_bullet_index: int | None = None

    for line in body_lines:

        # --------------------------------------------------------------
        # New Point
        # --------------------------------------------------------------

        point_match = _POINT_PATTERN.match(line)

        if point_match:

            if current_point is not None:
                reply_points.append(current_point)

            current_point = ReplyPoint(
                number=int(point_match.group(1)),
                title=point_match.group(2).strip(),
                content=[],
            )

            current_bullet_index = None

            continue

        # --------------------------------------------------------------
        # New bullet
        # --------------------------------------------------------------

        if line.startswith("●"):

            if current_point is None:
                raise ValueError(
                    "Reply content encountered before first Point."
                )

            content = line[1:].strip()

            if content:
                current_point.content.append(content)

                current_bullet_index = (
                    len(current_point.content) - 1
                )

            continue

        # --------------------------------------------------------------
        # Wrapped continuation
        # --------------------------------------------------------------

        if (
            current_point is not None
            and current_bullet_index is not None
        ):
            current_point.content[current_bullet_index] = (
                f"{current_point.content[current_bullet_index]} {line}"
            )

            continue

        # --------------------------------------------------------------
        # Unexpected content
        # --------------------------------------------------------------

        raise ValueError(
            f"Unexpected line in reply-points section: {line!r}"
        )

    # Add the final point.
    if current_point is not None:
        reply_points.append(current_point)

    if not reply_points:
        raise ValueError(
            "No reply points were extracted."
        )

    # ------------------------------------------------------------------
    # Validate numbering.
    # ------------------------------------------------------------------

    actual_numbers = [
        point.number
        for point in reply_points
    ]

    expected_numbers = list(
        range(1, len(reply_points) + 1)
    )

    if actual_numbers != expected_numbers:
        raise ValueError(
            "Reply points are not sequentially numbered. "
            f"Expected {expected_numbers}, got {actual_numbers}."
        )

    # ------------------------------------------------------------------
    # Validate content.
    # ------------------------------------------------------------------

    for point in reply_points:

        if not point.content:
            raise ValueError(
                f"Reply Point {point.number} has no content."
            )

    return reply_points


# ============================================================================
# SECTION 4 — PRAYER
# ============================================================================

def _extract_prayer(
    section: str,
) -> str:
    lines = [
        _clean_line(line)
        for line in section.splitlines()
        if _clean_line(line)
    ]

    if not lines or lines[0] != "4. Prayer":
        raise ValueError(
            "Unexpected prayer section heading."
        )

    prayer_lines = [
        line[1:].strip()
        for line in lines[1:]
        if line.startswith("●")
    ]

    if len(prayer_lines) != 1:
        raise ValueError(
            "Expected exactly one prayer statement, "
            f"found {len(prayer_lines)}."
        )

    return prayer_lines[0]


# ============================================================================
# SECTION 5 — ATTESTATION
# ============================================================================

def _extract_attestation(
    section: str,
) -> dict[str, str]:
    known_fields = {
        "Place",
        "Date",
    }

    return _extract_labelled_fields(
        section,
        heading="5. Attestation Details",
        known_fields=known_fields,
    )


# ============================================================================
# SECTION 6 — ADVOCATE
# ============================================================================

def _remove_document_footer(
    lines: list[str],
) -> list[str]:
    """
    Remove the assignment footer appearing after the advocate details.

    The PDF may wrap the footer over multiple physical lines.
    """
    cleaned: list[str] = []

    footer_started = False

    for line in lines:

        if line.startswith(
            "This file contains input data only."
        ):
            footer_started = True
            continue

        if footer_started:
            continue

        cleaned.append(line)

    return cleaned


def _extract_advocate_details(
    section: str,
) -> dict[str, str]:
    lines = [
        _clean_line(line)
        for line in section.splitlines()
        if _clean_line(line)
    ]

    lines = _remove_document_footer(lines)

    if not lines or lines[0] != "6. Advocate":
        raise ValueError(
            "Unexpected advocate section heading."
        )

    known_fields = {
        "Advocate Firm",
        "Acting for",
    }

    cleaned_section = "\n".join(lines)

    return _extract_labelled_fields(
        cleaned_section,
        heading="6. Advocate",
        known_fields=known_fields,
    )


# ============================================================================
# EXHIBIT
# ============================================================================

_EXHIBIT_PATTERN = re.compile(
    r"EXHIBIT[-–—][‘'\"A-Za-z0-9]+[’'\"]?"
)


def _extract_exhibit(
    reply_points: list[ReplyPoint],
) -> str:
    """
    Extract the exhibit marker supplied in the reply-point content.
    """
    for point in reply_points:
        for statement in point.content:

            match = _EXHIBIT_PATTERN.search(statement)

            if match:
                return match.group(0)

    return ""


# ============================================================================
# PUBLIC API
# ============================================================================

def extract_case_data(
    pages: list[str],
) -> CaseData:
    """
    Convert Phase 1 PDF extraction output into CaseData.

    The supplied case-information document is structured and labelled,
    therefore deterministic extraction is used instead of an LLM.
    """
    text = _normalize_text(pages)

    sections = _split_sections(text)

    case_data = CaseData()

    # ------------------------------------------------------------------
    # 1. Court and Case Details
    # ------------------------------------------------------------------

    court_case_fields = _extract_court_case_details(
        sections["court_case_details"]
    )

    _populate_court_case_data(
        case_data,
        court_case_fields,
    )

    # ------------------------------------------------------------------
    # 2. Deponent Details
    # ------------------------------------------------------------------

    deponent_fields = _extract_deponent_details(
        sections["deponent_details"]
    )

    _populate_deponent_data(
        case_data,
        deponent_fields,
    )

    # ------------------------------------------------------------------
    # 3. Reply Points
    # ------------------------------------------------------------------

    case_data.reply_points = _extract_reply_points(
        sections["reply_points"]
    )

    # ------------------------------------------------------------------
    # 4. Prayer
    # ------------------------------------------------------------------

    case_data.prayer = _extract_prayer(
        sections["prayer"]
    )

    # ------------------------------------------------------------------
    # 5. Attestation
    # ------------------------------------------------------------------

    attestation_fields = _extract_attestation(
        sections["attestation"]
    )

    case_data.attestation_place = (
        attestation_fields["Place"]
    )

    case_data.attestation_date = (
        attestation_fields["Date"]
    )

    # ------------------------------------------------------------------
    # 6. Advocate
    # ------------------------------------------------------------------

    advocate_fields = _extract_advocate_details(
        sections["advocate"]
    )

    case_data.advocate_firm = (
        advocate_fields["Advocate Firm"]
    )

    case_data.advocate_for = (
        advocate_fields["Acting for"]
    )

    # ------------------------------------------------------------------
    # Exhibit
    # ------------------------------------------------------------------

    case_data.exhibit = _extract_exhibit(
        case_data.reply_points
    )

    return case_data