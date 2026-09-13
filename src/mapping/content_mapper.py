from __future__ import annotations

from dataclasses import dataclass, field

from src.extraction.case_schema import CaseData, ReplyPoint
from src.template.schema import TemplateSpecification


# ============================================================================
# CONTENT MAPPING DATA STRUCTURES
# ============================================================================

@dataclass
class ContentMapping:
    """
    Maps one logical template element to its source in CaseData.

    This is an intermediate representation. It does not contain
    generated legal prose.
    """

    target: str
    source: str
    value: str = ""
    template_rule: str = ""


@dataclass
class MappedParagraph:
    """
    Maps one numbered affidavit paragraph to its source reply point
    or to a template-defined closing move.
    """

    paragraph_number: int
    source_type: str
    source_reference: str
    title: str
    content: list[str] = field(default_factory=list)
    template_move: str = ""


@dataclass
class ContentMap:
    """
    Complete intermediate representation connecting CaseData with
    TemplateSpecification.

    Phase 4 document generation consumes this object.
    """

    document_type: str

    sections: list[ContentMapping] = field(default_factory=list)

    paragraphs: list[MappedParagraph] = field(default_factory=list)

    exhibit: ContentMapping | None = None

    prayer: ContentMapping | None = None

    jurat: ContentMapping | None = None

    verification: ContentMapping | None = None

    advocate: ContentMapping | None = None

    paragraph_count: int = 0


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def _validate_document_type(
    case_data: CaseData,
    template_specification: TemplateSpecification,
) -> None:
    if not case_data.document_type:
        raise ValueError("CaseData.document_type is empty.")

    if not template_specification.document_type:
        raise ValueError(
            "TemplateSpecification.document_type is empty."
        )

    if (
        case_data.document_type
        != template_specification.document_type
    ):
        raise ValueError(
            "Document type mismatch: "
            f"CaseData has {case_data.document_type!r}, "
            f"but TemplateSpecification has "
            f"{template_specification.document_type!r}."
        )


def _validate_case_data(case_data: CaseData) -> None:
    required_values = {
        "court": case_data.court,
        "jurisdiction": case_data.jurisdiction,
        "proceeding_type": case_data.proceeding_type,
        "case_number": case_data.case_number,
        "year": case_data.year,
        "petitioner": case_data.petitioner,
        "filed_on_behalf_of": case_data.filed_on_behalf_of,
        "deponent_name": case_data.deponent_name,
        "designation": case_data.designation,
        "organisation": case_data.organisation,
        "address": case_data.address,
        "verification_verb": case_data.verification_verb,
        "prayer": case_data.prayer,
        "attestation_place": case_data.attestation_place,
        "attestation_date": case_data.attestation_date,
        "advocate_firm": case_data.advocate_firm,
        "advocate_for": case_data.advocate_for,
    }

    missing = [
        field_name
        for field_name, value in required_values.items()
        if not value
    ]

    if missing:
        raise ValueError(
            "CaseData is missing required values: "
            + ", ".join(sorted(missing))
        )

    if not case_data.respondents:
        raise ValueError("CaseData contains no respondents.")

    if not case_data.reply_points:
        raise ValueError("CaseData contains no reply points.")


def _validate_reply_points(
    reply_points: list[ReplyPoint],
) -> None:
    expected_numbers = list(
        range(1, len(reply_points) + 1)
    )

    actual_numbers = [
        point.number
        for point in reply_points
    ]

    if actual_numbers != expected_numbers:
        raise ValueError(
            "Reply points are not sequentially numbered. "
            f"Expected {expected_numbers}, got {actual_numbers}."
        )

    for point in reply_points:
        if not point.title:
            raise ValueError(
                f"Reply Point {point.number} has no title."
            )

        if not point.content:
            raise ValueError(
                f"Reply Point {point.number} has no content."
            )


def _validate_template_sections(
    template_specification: TemplateSpecification,
) -> None:
    required_sections = {
        "FORUM_HEADING",
        "JURISDICTION",
        "CASE_NUMBER",
        "CAUSE_TITLE",
        "AFFIDAVIT_TITLE",
        "DEPONENT_CLAUSE",
        "NUMBERED_PARAGRAPHS",
        "PRAYER",
        "JURAT",
        "VERIFICATION",
    }

    available_sections = {
        section.name
        for section in template_specification.sections
    }

    missing = required_sections - available_sections

    if missing:
        raise ValueError(
            "TemplateSpecification is missing required sections: "
            + ", ".join(sorted(missing))
        )


# ============================================================================
# TEMPLATE MOVE HELPERS
# ============================================================================

def _find_reply_move(
    template_specification: TemplateSpecification,
    move_name: str,
) -> str:
    """
    Return the purpose of a named template reply move.

    The mapper uses the move name as the stable identifier and retains
    its template-defined purpose for downstream generation.
    """

    for move in template_specification.reply_moves:
        if move.name == move_name:
            return move.purpose

    raise ValueError(
        f"Required reply move not found: {move_name}"
    )


def _resolve_reply_move(
    point_number: int,
    template_specification: TemplateSpecification,
) -> str:
    """
    Resolve a supplied reply point to the appropriate template move.

    The supplied case is intentionally mapped according to the
    deterministic reply-move sequence defined in Phase 2.
    """

    mapping = {
        1: "IDENTITY_AND_PERUSAL",
        2: "BLANKET_DENIAL",
        3: "PRELIMINARY_POSITION",
        4: "SUBSTANTIVE_ANSWER",
        5: "SUBSTANTIVE_ANSWER",
        6: "SUBSTANTIVE_ANSWER",
    }

    move_name = mapping.get(
        point_number,
        "SUBSTANTIVE_ANSWER",
    )

    _find_reply_move(
        template_specification,
        move_name,
    )

    return move_name


def _resolve_closing_move(
    template_specification: TemplateSpecification,
) -> str:
    move_name = "CLOSING"

    _find_reply_move(
        template_specification,
        move_name,
    )

    return move_name


# ============================================================================
# SECTION MAPPING
# ============================================================================

def _build_section_mappings(
    case_data: CaseData,
    template_specification: TemplateSpecification,
) -> list[ContentMapping]:
    """
    Map case entities to the ten structural template sections.
    """

    respondent_1 = case_data.respondents.get("1", "")
    respondent_2 = case_data.respondents.get("2", "")

    if not respondent_1:
        raise ValueError(
            "Respondent No. 1 is required for cause-title mapping."
        )

    if not respondent_2:
        raise ValueError(
            "Respondent No. 2 is required for cause-title mapping."
        )

    sections = [
        ContentMapping(
            target="FORUM_HEADING",
            source="CaseData.court",
            value=case_data.court,
        ),
        ContentMapping(
            target="JURISDICTION",
            source="CaseData.jurisdiction",
            value=case_data.jurisdiction,
        ),
        ContentMapping(
            target="CASE_NUMBER",
            source=(
                "CaseData.proceeding_type + "
                "CaseData.case_number + CaseData.year"
            ),
            value=(
                f"{case_data.proceeding_type} "
                f"No. {case_data.case_number} of "
                f"{case_data.year}"
            ),
        ),
        ContentMapping(
            target="CAUSE_TITLE",
            source=(
                "CaseData.petitioner + "
                "CaseData.respondents"
            ),
            value=(
                f"{case_data.petitioner} "
                f"vs. {respondent_1} and {respondent_2}"
            ),
        ),
        ContentMapping(
            target="AFFIDAVIT_TITLE",
            source="CaseData.document_type",
            value=case_data.document_type,
        ),
        ContentMapping(
            target="DEPONENT_CLAUSE",
            source=(
                "CaseData.deponent_name + "
                "CaseData.designation + "
                "CaseData.organisation + "
                "CaseData.filed_on_behalf_of"
            ),
            value=(
                f"{case_data.deponent_name}, "
                f"{case_data.designation}, "
                f"{case_data.organisation}, "
                f"{case_data.filed_on_behalf_of}"
            ),
        ),
    ]

    # Ensure every mapped target corresponds to a known template section.
    template_section_names = {
        section.name
        for section in template_specification.sections
    }

    for mapping in sections:
        if mapping.target not in template_section_names:
            raise ValueError(
                f"Mapped target is not present in template: "
                f"{mapping.target}"
            )

    return sections


# ============================================================================
# PARAGRAPH MAPPING
# ============================================================================

def _build_paragraph_mappings(
    case_data: CaseData,
    template_specification: TemplateSpecification,
) -> list[MappedParagraph]:
    """
    Map each supplied ReplyPoint to one numbered affidavit paragraph,
    followed by the template-defined closing paragraph.
    """

    paragraphs: list[MappedParagraph] = []

    for point in case_data.reply_points:

        move_name = _resolve_reply_move(
            point.number,
            template_specification,
        )

        paragraphs.append(
            MappedParagraph(
                paragraph_number=point.number,
                source_type="case_reply_point",
                source_reference=(
                    f"CaseData.reply_points[{point.number - 1}]"
                ),
                title=point.title,
                content=list(point.content),
                template_move=move_name,
            )
        )

    closing_move = _resolve_closing_move(
        template_specification,
    )

    closing_number = len(paragraphs) + 1

    paragraphs.append(
        MappedParagraph(
            paragraph_number=closing_number,
            source_type="template_move",
            source_reference="TemplateSpecification.reply_moves[CLOSING]",
            title="Closing",
            content=[],
            template_move=closing_move,
        )
    )

    return paragraphs


# ============================================================================
# SUPPORTING MAPPINGS
# ============================================================================

def _build_exhibit_mapping(
    case_data: CaseData,
) -> ContentMapping | None:
    if not case_data.exhibit:
        return None

    return ContentMapping(
        target="EXHIBIT",
        source="CaseData.exhibit",
        value=case_data.exhibit,
    )


def _build_prayer_mapping(
    case_data: CaseData,
) -> ContentMapping:
    return ContentMapping(
        target="PRAYER",
        source="CaseData.prayer",
        value=case_data.prayer,
    )


def _build_jurat_mapping(
    case_data: CaseData,
) -> ContentMapping:
    return ContentMapping(
        target="JURAT",
        source=(
            "CaseData.verification_verb + "
            "CaseData.deponent_name + "
            "CaseData.attestation_place + "
            "CaseData.attestation_date"
        ),
        value=(
            f"{case_data.verification_verb}; "
            f"{case_data.deponent_name}; "
            f"{case_data.attestation_place}; "
            f"{case_data.attestation_date}"
        ),
    )


def _build_verification_mapping(
    case_data: CaseData,
    paragraph_count: int,
) -> ContentMapping:
    return ContentMapping(
        target="VERIFICATION",
        source=(
            "CaseData.verification_verb + "
            "mapped paragraph count"
        ),
        value=(
            f"{case_data.verification_verb}; "
            f"paragraphs 1 to {paragraph_count} "
            f"and the Prayer"
        ),
    )


def _build_advocate_mapping(
    case_data: CaseData,
) -> ContentMapping:
    return ContentMapping(
        target="ADVOCATE",
        source=(
            "CaseData.advocate_firm + "
            "CaseData.advocate_for"
        ),
        value=(
            f"{case_data.advocate_firm}; "
            f"{case_data.advocate_for}"
        ),
    )


# ============================================================================
# PUBLIC API
# ============================================================================

def build_content_map(
    case_data: CaseData,
    template_specification: TemplateSpecification,
) -> ContentMap:
    """
    Build the deterministic content map consumed by Phase 4.

    No legal prose is generated here.

    The mapper only:
        1. validates CaseData and TemplateSpecification,
        2. connects case entities to template sections,
        3. maps reply points to numbered paragraphs,
        4. preserves exhibit/prayer/attestation/advocate information,
        5. records the resulting paragraph count.
    """

    _validate_document_type(
        case_data,
        template_specification,
    )

    _validate_case_data(case_data)

    _validate_reply_points(
        case_data.reply_points,
    )

    _validate_template_sections(
        template_specification,
    )

    sections = _build_section_mappings(
        case_data,
        template_specification,
    )

    paragraphs = _build_paragraph_mappings(
        case_data,
        template_specification,
    )

    paragraph_count = len(paragraphs)

    return ContentMap(
        document_type=case_data.document_type,
        sections=sections,
        paragraphs=paragraphs,
        exhibit=_build_exhibit_mapping(case_data),
        prayer=_build_prayer_mapping(case_data),
        jurat=_build_jurat_mapping(case_data),
        verification=_build_verification_mapping(
            case_data,
            paragraph_count,
        ),
        advocate=_build_advocate_mapping(case_data),
        paragraph_count=paragraph_count,
    )