from __future__ import annotations

import json
import re
from typing import Any

from langchain_ollama import ChatOllama

from src.agent.state import AgentState


# ============================================================================
# MODEL CONFIGURATION
# ============================================================================

MODEL_NAME = "qwen2.5:7b"


# ============================================================================
# EVALUATION WEIGHTS
# ============================================================================

EVALUATION_WEIGHTS = {
    "Entity Accuracy": 0.20,
    "Completeness": 0.20,
    "Structure": 0.15,
    "Consistency": 0.15,
    "Template Fidelity": 0.15,
    "Hallucination Check": 0.15,
}


# ============================================================================
# SEMANTIC OUTPUT SCHEMA
# ============================================================================

SEMANTIC_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "semantic_checks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "dimension": {
                        "type": "string",
                    },
                    "passed": {
                        "type": "boolean",
                    },
                    "severity": {
                        "type": "string",
                    },
                    "issue": {
                        "type": "string",
                    },
                    "evidence": {
                        "type": "string",
                    },
                    "source_reference": {
                        "type": "string",
                    },
                },
                "required": [
                    "dimension",
                    "passed",
                    "severity",
                    "issue",
                    "evidence",
                    "source_reference",
                ],
                "additionalProperties": False,
            },
        },
        "summary": {
            "type": "string",
        },
    },
    "required": [
        "semantic_checks",
        "summary",
    ],
    "additionalProperties": False,
}


# ============================================================================
# SERIALIZATION
# ============================================================================

def _case_data_to_dict(
    case_data: Any,
) -> dict[str, Any]:
    """
    Convert CaseData into JSON-safe data.
    """

    result: dict[str, Any] = {}

    for field_name in case_data.__dataclass_fields__:
        value = getattr(
            case_data,
            field_name,
        )

        if isinstance(value, list):
            converted = []

            for item in value:
                if hasattr(
                    item,
                    "__dataclass_fields__",
                ):
                    converted.append(
                        {
                            field: getattr(
                                item,
                                field,
                            )
                            for field in item.__dataclass_fields__
                        }
                    )
                else:
                    converted.append(item)

            result[field_name] = converted

        elif hasattr(
            value,
            "__dataclass_fields__",
        ):
            result[field_name] = {
                field: getattr(
                    value,
                    field,
                )
                for field in value.__dataclass_fields__
            }

        else:
            result[field_name] = value

    return result


def _template_to_dict(
    template: Any,
) -> dict[str, Any]:
    """
    Convert TemplateSpecification into JSON-safe data.
    """

    return {
        "document_type": template.document_type,
        "sections": [
            {
                "order": section.order,
                "name": section.name,
                "required": section.required,
                "formatting": section.formatting,
                "notes": section.notes,
            }
            for section in template.sections
        ],
        "entities": template.entities,
        "reply_moves": [
            {
                "name": move.name,
                "purpose": move.purpose,
                "expected_position": move.expected_position,
            }
            for move in template.reply_moves
        ],
        "fixed_phrases": template.fixed_phrases,
        "formatting_rules": template.formatting_rules,
        "consistency_rules": template.consistency_rules,
        "unsupported_elements": template.unsupported_elements,
    }


def _content_map_to_dict(
    content_map: Any,
) -> dict[str, Any]:
    """
    Convert ContentMap into JSON-safe data.
    """

    def mapping_to_dict(
        mapping: Any,
    ) -> dict[str, Any] | None:
        if mapping is None:
            return None

        return {
            "target": mapping.target,
            "source": mapping.source,
            "value": mapping.value,
            "template_rule": mapping.template_rule,
        }

    return {
        "document_type": content_map.document_type,
        "sections": [
            mapping_to_dict(item)
            for item in content_map.sections
        ],
        "paragraphs": [
            {
                "paragraph_number": item.paragraph_number,
                "source_type": item.source_type,
                "source_reference": item.source_reference,
                "title": item.title,
                "content": item.content,
                "template_move": item.template_move,
            }
            for item in content_map.paragraphs
        ],
        "exhibit": mapping_to_dict(
            content_map.exhibit
        ),
        "prayer": mapping_to_dict(
            content_map.prayer
        ),
        "jurat": mapping_to_dict(
            content_map.jurat
        ),
        "verification": mapping_to_dict(
            content_map.verification
        ),
        "advocate": mapping_to_dict(
            content_map.advocate
        ),
        "paragraph_count": content_map.paragraph_count,
    }


# ============================================================================
# COMMON HELPERS
# ============================================================================

def _deterministic_issue(
    dimension: str,
    issue: str,
    source: str,
    expected: Any = None,
    actual: Any = None,
    severity: str = "HIGH",
) -> dict[str, Any]:
    """
    Create a standardized deterministic evaluation issue.
    """

    result = {
        "dimension": dimension,
        "severity": severity,
        "issue": issue,
        "source_reference": source,
    }

    if expected is not None:
        result["expected"] = expected

    if actual is not None:
        result["actual"] = actual

    return result


def _semantic_issue(
    dimension: str,
    issue: str,
    evidence: str,
    source_reference: str,
    severity: str = "HIGH",
) -> dict[str, Any]:
    """
    Create a standardized semantic evaluation issue.
    """

    return {
        "dimension": dimension,
        "passed": False,
        "severity": severity,
        "issue": issue,
        "evidence": evidence,
        "source_reference": source_reference,
    }


def _contains(
    actual: str,
    expected: str,
) -> bool:
    """
    Case-insensitive substring check.
    """

    if not expected:
        return True

    return expected.lower() in actual.lower()


def _normalize_text(
    value: Any,
) -> str:
    """
    Normalize text for comparisons without modifying
    the generated draft.
    """

    if value is None:
        return ""

    return " ".join(
        str(value).strip().split()
    ).lower()


def _expected_jurat_verb(
    verification_verb: str,
) -> str:
    """
    Convert the Part 6 verification verb into the
    corresponding Part 9 jurat verb.
    """

    normalized = _normalize_text(
        verification_verb
    )

    if normalized == "solemnly affirm":
        return "solemnly affirmed"

    if normalized == "swear and affirm":
        return "sworn"

    if normalized == "affirm":
        return "affirmed"

    return ""


# ============================================================================
# DETERMINISTIC ENTITY CHECKS
# ============================================================================

def _deterministic_entity_checks(
    state: AgentState,
) -> list[dict[str, Any]]:
    """
    Validate objective entities against CaseData.
    """

    case = state["case_data"]
    draft = state["generated_draft"]

    issues: list[dict[str, Any]] = []

    sections = draft.get(
        "sections",
        {},
    )

    if not isinstance(sections, dict):
        return [
            _deterministic_issue(
                "Structure",
                "Generated draft sections are not an object.",
                "GeneratedDraft.sections",
                "object",
                type(sections).__name__,
            )
        ]

    checks = {
        "FORUM_HEADING": (
            case.court,
            sections.get(
                "FORUM_HEADING",
                "",
            ),
            "CaseData.court",
        ),
        "JURISDICTION": (
            case.jurisdiction,
            sections.get(
                "JURISDICTION",
                "",
            ),
            "CaseData.jurisdiction",
        ),
    }

    for (
        field_name,
        (
            expected,
            actual,
            source,
        ),
    ) in checks.items():

        if _normalize_text(actual) != _normalize_text(
            expected
        ):
            issues.append(
                _deterministic_issue(
                    "Entity Accuracy",
                    (
                        f"{field_name} does not match "
                        "the source value."
                    ),
                    source,
                    expected,
                    actual,
                )
            )

    expected_case_number = (
        f"{case.proceeding_type} "
        f"No. {case.case_number} of {case.year}"
    )

    actual_case_number = sections.get(
        "CASE_NUMBER",
        "",
    )

    if _normalize_text(
        actual_case_number
    ) != _normalize_text(
        expected_case_number
    ):
        issues.append(
            _deterministic_issue(
                "Entity Accuracy",
                "CASE_NUMBER does not match CaseData.",
                (
                    "CaseData.proceeding_type + "
                    "case_number + year"
                ),
                expected_case_number,
                actual_case_number,
            )
        )

    affidavit_title = sections.get(
        "AFFIDAVIT_TITLE",
        "",
    )

    if case.document_type and not _contains(
        affidavit_title,
        case.document_type,
    ):
        issues.append(
            _deterministic_issue(
                "Entity Accuracy",
                (
                    "Affidavit title does not contain "
                    "the required document type."
                ),
                "CaseData.document_type",
                case.document_type,
                affidavit_title,
            )
        )

    if case.filed_on_behalf_of and not _contains(
        affidavit_title,
        case.filed_on_behalf_of,
    ):
        issues.append(
            _deterministic_issue(
                "Entity Accuracy",
                (
                    "Affidavit title does not identify "
                    "the correct respondent."
                ),
                "CaseData.filed_on_behalf_of",
                case.filed_on_behalf_of,
                affidavit_title,
            )
        )

    cause_title = sections.get(
        "CAUSE_TITLE",
        "",
    )

    expected_parties = [
        case.petitioner,
        *case.respondents.values(),
    ]

    for party in expected_parties:

        if party and not _contains(
            cause_title,
            party,
        ):
            issues.append(
                _deterministic_issue(
                    "Entity Accuracy",
                    f"Cause title is missing party: {party}.",
                    "CaseData.petitioner / respondents",
                    party,
                    cause_title,
                )
            )

    deponent_clause = sections.get(
        "DEPONENT_CLAUSE",
        "",
    )

    for value, source in [
        (
            case.deponent_name,
            "CaseData.deponent_name",
        ),
        (
            case.designation,
            "CaseData.designation",
        ),
        (
            case.organisation,
            "CaseData.organisation",
        ),
        (
            case.filed_on_behalf_of,
            "CaseData.filed_on_behalf_of",
        ),
    ]:

        if value and not _contains(
            deponent_clause,
            value,
        ):
            issues.append(
                _deterministic_issue(
                    "Entity Accuracy",
                    f"Deponent clause is missing: {value}.",
                    source,
                    value,
                    deponent_clause,
                )
            )

    return issues


# ============================================================================
# DETERMINISTIC COMPLETENESS CHECKS
# ============================================================================

def _deterministic_completeness_checks(
    state: AgentState,
) -> list[dict[str, Any]]:
    """
    Verify that mapped source content is represented in the draft.
    """

    content_map = state["content_map"]
    draft = state["generated_draft"]

    issues: list[dict[str, Any]] = []

    paragraphs = draft.get(
        "paragraphs",
        [],
    )

    if not isinstance(
        paragraphs,
        list,
    ):
        return [
            _deterministic_issue(
                "Completeness",
                "Generated paragraphs are not a list.",
                "GeneratedDraft.paragraphs",
                "list",
                type(paragraphs).__name__,
            )
        ]

    expected_count = content_map.paragraph_count

    if len(paragraphs) != expected_count:
        issues.append(
            _deterministic_issue(
                "Completeness",
                "Generated paragraph count differs from ContentMap.",
                "ContentMap.paragraph_count",
                expected_count,
                len(paragraphs),
            )
        )

    for mapped in content_map.paragraphs:

        matching = next(
            (
                paragraph
                for paragraph in paragraphs
                if isinstance(paragraph, dict)
                and paragraph.get(
                    "paragraph_number"
                ) == mapped.paragraph_number
            ),
            None,
        )

        if matching is None:
            issues.append(
                _deterministic_issue(
                    "Completeness",
                    (
                        f"Mapped paragraph "
                        f"{mapped.paragraph_number} is missing."
                    ),
                    "ContentMap.paragraphs",
                    mapped.title,
                    None,
                )
            )
            continue

        content = matching.get(
            "content",
            "",
        )

        if not isinstance(
            content,
            str,
        ) or not content.strip():
            issues.append(
                _deterministic_issue(
                    "Completeness",
                    (
                        f"Mapped paragraph "
                        f"{mapped.paragraph_number} "
                        "contains no substantive content."
                    ),
                    (
                        "ContentMap.paragraphs"
                        f"[{mapped.paragraph_number}]"
                    ),
                    "non-empty substantive content",
                    content,
                )
            )

    if content_map.exhibit:

        actual_exhibit = draft.get(
            "exhibit",
            "",
        )

        if _normalize_text(
            actual_exhibit
        ) != _normalize_text(
            content_map.exhibit.value
        ):
            issues.append(
                _deterministic_issue(
                    "Completeness",
                    "Exhibit marker does not match ContentMap.",
                    "ContentMap.exhibit",
                    content_map.exhibit.value,
                    actual_exhibit,
                )
            )

    if content_map.prayer:

        actual_prayer = draft.get(
            "prayer",
            "",
        )

        if _normalize_text(
            actual_prayer
        ) != _normalize_text(
            content_map.prayer.value
        ):
            issues.append(
                _deterministic_issue(
                    "Completeness",
                    "Prayer does not match ContentMap.",
                    "ContentMap.prayer",
                    content_map.prayer.value,
                    actual_prayer,
                )
            )

    return issues


# ============================================================================
# DETERMINISTIC STRUCTURE CHECKS
# ============================================================================

def _deterministic_structure_checks(
    state: AgentState,
) -> list[dict[str, Any]]:
    """
    Validate structural completeness.
    """

    template = state["template_specification"]
    draft = state["generated_draft"]

    issues: list[dict[str, Any]] = []

    sections = draft.get(
        "sections",
        {},
    )

    required_header_sections = {
        "FORUM_HEADING",
        "JURISDICTION",
        "CASE_NUMBER",
        "CAUSE_TITLE",
        "AFFIDAVIT_TITLE",
        "DEPONENT_CLAUSE",
    }

    if not isinstance(
        sections,
        dict,
    ):
        issues.append(
            _deterministic_issue(
                "Structure",
                "Draft sections must be an object.",
                "GeneratedDraft.sections",
                "object",
                type(sections).__name__,
            )
        )
    else:
        for name in required_header_sections:

            value = sections.get(
                name
            )

            if not isinstance(
                value,
                str,
            ) or not value.strip():

                issues.append(
                    _deterministic_issue(
                        "Structure",
                        f"Required section '{name}' is missing.",
                        "TemplateSpecification.sections",
                        name,
                        value,
                    )
                )

    paragraphs = draft.get(
        "paragraphs",
        [],
    )

    expected_numbers = list(
        range(
            1,
            state["content_map"].paragraph_count + 1,
        )
    )

    if isinstance(
        paragraphs,
        list,
    ):
        actual_numbers = [
            paragraph.get(
                "paragraph_number"
            )
            if isinstance(
                paragraph,
                dict,
            )
            else None
            for paragraph in paragraphs
        ]

        if actual_numbers != expected_numbers:
            issues.append(
                _deterministic_issue(
                    "Structure",
                    "Paragraph numbering is not sequential.",
                    "ContentMap.paragraph_count",
                    expected_numbers,
                    actual_numbers,
                )
            )

    for field_name, section_name in [
        (
            "prayer",
            "PRAYER",
        ),
        (
            "jurat",
            "JURAT",
        ),
        (
            "verification",
            "VERIFICATION",
        ),
    ]:

        value = draft.get(
            field_name
        )

        if not isinstance(
            value,
            str,
        ) or not value.strip():

            issues.append(
                _deterministic_issue(
                    "Structure",
                    f"Required section '{section_name}' is missing.",
                    "TemplateSpecification.sections",
                    section_name,
                    value,
                )
            )

    represented_sections = (
        required_header_sections
        | {
            "NUMBERED_PARAGRAPHS",
            "PRAYER",
            "JURAT",
            "VERIFICATION",
        }
    )

    required_template_sections = {
        section.name
        for section in template.sections
        if section.required
    }

    missing_representations = (
        required_template_sections
        - represented_sections
    )

    for section in missing_representations:

        issues.append(
            _deterministic_issue(
                "Structure",
                (
                    f"Template section '{section}' has no "
                    "evaluation representation."
                ),
                "TemplateSpecification.sections",
                section,
                None,
            )
        )

    return issues


# ============================================================================
# DETERMINISTIC CONSISTENCY CHECKS
# ============================================================================

def _deterministic_consistency_checks(
    state: AgentState,
) -> list[dict[str, Any]]:
    """
    Validate cross-field consistency.
    """

    case = state["case_data"]
    content_map = state["content_map"]
    draft = state["generated_draft"]

    issues: list[dict[str, Any]] = []

    sections = draft.get(
        "sections",
        {},
    )

    affidavit_title = sections.get(
        "AFFIDAVIT_TITLE",
        "",
    )

    if case.filed_on_behalf_of and not _contains(
        affidavit_title,
        case.filed_on_behalf_of,
    ):
        issues.append(
            _deterministic_issue(
                "Consistency",
                (
                    "Affidavit title has incorrect "
                    "respondent identification."
                ),
                "CaseData.filed_on_behalf_of",
                case.filed_on_behalf_of,
                affidavit_title,
            )
        )

    deponent_clause = sections.get(
        "DEPONENT_CLAUSE",
        "",
    )

    if case.filed_on_behalf_of and not _contains(
        deponent_clause,
        case.filed_on_behalf_of,
    ):
        issues.append(
            _deterministic_issue(
                "Consistency",
                (
                    "Deponent clause has incorrect "
                    "respondent identification."
                ),
                "CaseData.filed_on_behalf_of",
                case.filed_on_behalf_of,
                deponent_clause,
            )
        )

    verification = draft.get(
        "verification",
        "",
    )

    expected_range = (
        f"paragraphs 1 to "
        f"{content_map.paragraph_count}"
    )

    if not _contains(
        verification,
        expected_range,
    ):
        issues.append(
            _deterministic_issue(
                "Consistency",
                (
                    "Verification range does not "
                    "match generated paragraph count."
                ),
                "ContentMap.paragraph_count",
                expected_range,
                verification,
            )
        )

    if not re.search(
        r"\bdo hereby verify\b",
        verification,
        flags=re.IGNORECASE,
    ):
        issues.append(
            _deterministic_issue(
                "Consistency",
                (
                    "Verification does not contain "
                    "the required 'do hereby verify' wording."
                ),
                "TemplateSpecification Part 10",
                "do hereby verify",
                verification,
            )
        )

    jurat = draft.get(
        "jurat",
        "",
    )

    expected_jurat_verb = _expected_jurat_verb(
        case.verification_verb
    )

    if expected_jurat_verb and not _contains(
        jurat,
        expected_jurat_verb,
    ):
        issues.append(
            _deterministic_issue(
                "Consistency",
                (
                    "Jurat verb does not match "
                    "the Part 6 verification verb."
                ),
                "CaseData.verification_verb + TemplateSpecification Part 9",
                expected_jurat_verb,
                jurat,
            )
        )

    for value, source in [
        (
            case.deponent_name,
            "CaseData.deponent_name",
        ),
        (
            case.attestation_place,
            "CaseData.attestation_place",
        ),
        (
            case.attestation_date,
            "CaseData.attestation_date",
        ),
    ]:

        if value and not _contains(
            jurat,
            value,
        ):
            issues.append(
                _deterministic_issue(
                    "Consistency",
                    f"Jurat is missing: {value}.",
                    source,
                    value,
                    jurat,
                )
            )

    for value, source in [
        (
            case.deponent_name,
            "CaseData.deponent_name",
        ),
        (
            case.attestation_place,
            "CaseData.attestation_place",
        ),
        (
            case.attestation_date,
            "CaseData.attestation_date",
        ),
    ]:

        if value and not _contains(
            verification,
            value,
        ):
            issues.append(
                _deterministic_issue(
                    "Consistency",
                    f"Verification is missing: {value}.",
                    source,
                    value,
                    verification,
                )
            )

    return issues


# ============================================================================
# DETERMINISTIC HALLUCINATION CHECKS
# ============================================================================

def _deterministic_hallucination_checks(
    state: AgentState,
) -> list[dict[str, Any]]:
    """
    Detect high-confidence factual contradictions.

    Only the dedicated CASE_NUMBER field is inspected for
    case-number contradictions.
    """

    case = state["case_data"]
    draft = state["generated_draft"]

    issues: list[dict[str, Any]] = []

    sections = draft.get(
        "sections",
        {},
    )

    if not isinstance(
        sections,
        dict,
    ):
        return issues

    actual_case_number = str(
        sections.get(
            "CASE_NUMBER",
            "",
        )
    )

    expected_case_number = str(
        case.case_number
    ).strip()

    numbers = re.findall(
        r"\bNo\.\s*(\d+)\b",
        actual_case_number,
        flags=re.IGNORECASE,
    )

    if numbers:

        unique_numbers = list(
            dict.fromkeys(numbers)
        )

        for generated_number in unique_numbers:

            if generated_number != expected_case_number:

                issues.append(
                    _deterministic_issue(
                        "Hallucination Check",
                        (
                            "Generated case number conflicts "
                            "with CaseData."
                        ),
                        "CaseData.case_number",
                        expected_case_number,
                        generated_number,
                    )
                )

    actual_year_matches = re.findall(
        r"\b20\d{2}\b",
        actual_case_number,
    )

    expected_year = str(
        case.year
    ).strip()

    unique_years = list(
        dict.fromkeys(
            actual_year_matches
        )
    )

    for generated_year in unique_years:

        if generated_year != expected_year:

            issues.append(
                _deterministic_issue(
                    "Hallucination Check",
                    (
                        "Generated case-number year "
                        "is not supported by CaseData."
                    ),
                    "CaseData.year",
                    expected_year,
                    generated_year,
                )
            )

    return issues


# ============================================================================
# SEMANTIC PROMPT
# ============================================================================

def _build_semantic_prompt(
    state: AgentState,
) -> str:
    """
    Build the single local-Qwen semantic evaluation prompt.
    """

    case_data = _case_data_to_dict(
        state["case_data"]
    )

    template = _template_to_dict(
        state["template_specification"]
    )

    content_map = _content_map_to_dict(
        state["content_map"]
    )

    draft = state["generated_draft"]

    return f"""
You are the semantic evaluator in a hybrid evaluator for an
AI-generated Affidavit in Reply.

Python separately checks objective fields and structure.

Your responsibility is ONLY semantic analysis.

You MUST actively look for genuine semantic failures.

Allowed dimensions:

- Completeness
- Template Fidelity
- Hallucination Check

Do NOT evaluate:
- exact case number
- exact year
- exact party names
- respondent number
- exact dates
- exact exhibit marker
- paragraph count
- paragraph numbering
- exact formatting

Those are handled by Python.

============================================================
IMPORTANT
============================================================

Do not assume that a paragraph is correct merely because it is
grammatically valid or legally phrased.

Compare the GENERATED CONTENT against the CONTENT MAP.

A paragraph fails semantic completeness when it loses a material
fact, denial, position, answer, or procedural point contained in
its mapped source.

A paragraph fails template fidelity when it does not actually
perform its assigned reply move.

A paragraph fails hallucination when it introduces a substantive
factual event or circumstance that cannot be supported by the
CaseData or ContentMap.

============================================================
CASE DATA
============================================================

{json.dumps(
    case_data,
    indent=2,
    ensure_ascii=False,
)}

============================================================
TEMPLATE SPECIFICATION
============================================================

{json.dumps(
    template,
    indent=2,
    ensure_ascii=False,
)}

============================================================
CONTENT MAP
============================================================

{json.dumps(
    content_map,
    indent=2,
    ensure_ascii=False,
)}

============================================================
GENERATED DRAFT
============================================================

{json.dumps(
    draft,
    indent=2,
    ensure_ascii=False,
)}

============================================================
TASK 1 — SEMANTIC COMPLETENESS
============================================================

Review EVERY ContentMap paragraph.

For each paragraph:

1. Find the matching generated paragraph.
2. Read the source content.
3. Read the generated content.
4. Compare their substantive meaning.
5. Identify any material source point that has been lost.

Do not require word-for-word similarity.

Paraphrasing is allowed.

However, if a source paragraph contains a specific material
position and the generated paragraph reduces it to a generic
statement that does not preserve that position, report it.

Example:

SOURCE:
"Respondent No. 2 denies all statements, contentions and
averments except those specifically admitted."

GENERATED:
"With reference to the Petition, I deny the allegations."

This is materially weaker because it does not preserve the
specific blanket-denial position.

Report this as a semantic completeness/template-fidelity issue.

============================================================
TASK 2 — TEMPLATE / REPLY-MOVE FIDELITY
============================================================

Expected paragraph functions:

1. IDENTITY_AND_PERUSAL
2. BLANKET_DENIAL
3. PRELIMINARY_POSITION
4. SUBSTANTIVE_ANSWER
5. SUBSTANTIVE_ANSWER
6. SUBSTANTIVE_ANSWER
7. CLOSING

Check whether each generated paragraph actually performs its
assigned function.

Do not penalize reasonable legal paraphrasing.

============================================================
TASK 3 — SEMANTIC HALLUCINATION
============================================================

Look for unsupported factual assertions.

Examples that MUST be investigated:

- personally inspected a site
- conducted an investigation
- attended a meeting
- received an approval
- obtained a report
- personally reviewed evidence
- visited a location
- issued a communication not present in the sources
- participated in an event not present in the sources
- factual dates or events not supported by the sources

For every suspicious factual assertion:

1. Locate it in the generated paragraph.
2. Search CaseData and ContentMap for support.
3. If unsupported, report it.

Example:

GENERATED:
"I personally inspected the redevelopment site on 1 August 2026."

If neither CaseData nor ContentMap contains such an inspection,
this is an unsupported factual assertion and MUST be reported.

Do NOT flag ordinary legal drafting language such as:

- I say
- I submit
- I respectfully submit
- the present Petition
- the Petitioner
- with costs

============================================================
IMPORTANT CONSERVATIVE RULE
============================================================

Only report a semantic issue when there is actual evidence.

Do not invent problems.

Do not penalize wording differences.

Do not penalize polished legal drafting.

============================================================
OUTPUT
============================================================

For every genuine semantic failure:

passed = false

Provide:

dimension
severity
issue
evidence
source_reference

If there are no genuine semantic failures:

semantic_checks = []

Return ONLY JSON matching the supplied schema.
"""


# ============================================================================
# HIGH-CONFIDENCE SEMANTIC GUARDRAILS
# ============================================================================

def _semantic_guardrail_checks(
    state: AgentState,
) -> list[dict[str, Any]]:
    """
    Add high-confidence semantic findings that should not depend
    entirely on a small local model.

    These are intentionally narrow.

    The guardrails do NOT replace Qwen semantic evaluation.

    They protect the evaluator against obvious unsupported factual
    assertions and severe source-content reduction that a local
    model may occasionally overlook.
    """

    content_map = state["content_map"]
    draft = state["generated_draft"]

    issues: list[dict[str, Any]] = []

    paragraphs = draft.get(
        "paragraphs",
        [],
    )

    if not isinstance(
        paragraphs,
        list,
    ):
        return issues

    # ------------------------------------------------------------------------
    # Build paragraph lookup
    # ------------------------------------------------------------------------

    generated_by_number: dict[int, str] = {}

    for paragraph in paragraphs:

        if not isinstance(
            paragraph,
            dict,
        ):
            continue

        number = paragraph.get(
            "paragraph_number"
        )

        content = paragraph.get(
            "content",
            "",
        )

        if isinstance(
            number,
            int,
        ):
            generated_by_number[number] = str(
                content
            )

    # ------------------------------------------------------------------------
    # High-confidence unsupported factual assertions
    # ------------------------------------------------------------------------
    #
    # These patterns are deliberately narrow. They target assertions
    # of personal actions/events that would normally require source
    # support.
    # ------------------------------------------------------------------------

    unsupported_patterns = [
        (
            re.compile(
                r"\bI\s+(?:personally\s+)?inspected\b",
                flags=re.IGNORECASE,
            ),
            "personal inspection",
        ),
        (
            re.compile(
                r"\bI\s+(?:personally\s+)?visited\b",
                flags=re.IGNORECASE,
            ),
            "personal visit",
        ),
        (
            re.compile(
                r"\bI\s+(?:personally\s+)?attended\b",
                flags=re.IGNORECASE,
            ),
            "personal attendance",
        ),
        (
            re.compile(
                r"\bI\s+(?:personally\s+)?conducted\b",
                flags=re.IGNORECASE,
            ),
            "personal investigation/action",
        ),
        (
            re.compile(
                r"\bI\s+(?:personally\s+)?received\b",
                flags=re.IGNORECASE,
            ),
            "personal receipt of material",
        ),
    ]

    source_text = json.dumps(
        {
            "case_data": _case_data_to_dict(
                state["case_data"]
            ),
            "content_map": _content_map_to_dict(
                content_map
            ),
        },
        ensure_ascii=False,
    ).lower()

    for number, content in generated_by_number.items():

        if not content.strip():
            continue

        for pattern, action_name in unsupported_patterns:

            match = pattern.search(
                content
            )

            if not match:
                continue

            # Check whether the complete generated sentence has
            # meaningful source support. The narrow guardrail only
            # fires when the action itself is not represented in
            # the supplied source material.
            action_word = match.group(0).lower()

            if action_word not in source_text:

                issues.append(
                    _semantic_issue(
                        "Hallucination Check",
                        (
                            "Generated paragraph contains an "
                            f"unsupported factual assertion involving "
                            f"{action_name}."
                        ),
                        content,
                        (
                            f"ContentMap.paragraphs["
                            f"{number}] and CaseData"
                        ),
                    )
                )

    # ------------------------------------------------------------------------
    # High-confidence severe source reduction
    # ------------------------------------------------------------------------
    #
    # A paragraph mapped to a substantive point should not collapse
    # into a generic denial when the source contains materially more
    # specific information.
    #
    # This is intentionally limited to obvious generic-denial
    # reductions and therefore does not replace Qwen's semantic work.
    # ------------------------------------------------------------------------

    generic_denial_patterns = [
        re.compile(
            r"^\s*with reference to the petition,\s*"
            r"i\s+deny\s+the\s+allegations\.?\s*$",
            flags=re.IGNORECASE,
        ),
        re.compile(
            r"^\s*i\s+deny\s+the\s+allegations\.?\s*$",
            flags=re.IGNORECASE,
        ),
    ]

    for mapped in content_map.paragraphs:

        number = mapped.paragraph_number

        generated = generated_by_number.get(
            number,
            "",
        ).strip()

        if not generated:
            continue

        is_generic_denial = any(
            pattern.fullmatch(
                generated
            )
            for pattern in generic_denial_patterns
        )

        if not is_generic_denial:
            continue

        source_content = " ".join(
            mapped.content
        ).strip()

        if not source_content:
            continue

        # A generic denial replacing a mapped point is only flagged
        # when the source itself contains materially specific
        # substantive content.
        source_normalized = _normalize_text(
            source_content
        )

        specific_markers = [
            "except",
            "specifically admitted",
            "authority",
            "pursuant",
            "procedure",
            "communication",
            "records",
            "relies",
            "annexed",
            "exhibit",
            "costs",
        ]

        has_specific_source_content = any(
            marker in source_normalized
            for marker in specific_markers
        )

        if has_specific_source_content:

            issues.append(
                _semantic_issue(
                    "Completeness",
                    (
                        f"Generated paragraph {number} "
                        "reduces a materially specific mapped "
                        "source point to a generic denial."
                    ),
                    generated,
                    (
                        f"ContentMap.paragraphs["
                        f"{number}]"
                    ),
                )
            )

    return issues


# ============================================================================
# SEMANTIC EVALUATION
# ============================================================================

def _run_semantic_evaluation(
    state: AgentState,
) -> dict[str, Any]:
    """
    Execute local-Qwen semantic evaluation and combine it with
    narrow high-confidence semantic guardrails.

    Qwen remains the primary semantic evaluator.

    Guardrails exist only for obvious failures that a small local
    model may overlook.
    """

    model = ChatOllama(
        model=MODEL_NAME,
        temperature=0,
    )

    structured_model = model.with_structured_output(
        SEMANTIC_JSON_SCHEMA,
        method="json_schema",
    )

    result = structured_model.invoke(
        _build_semantic_prompt(state)
    )

    model_checks = result.get(
        "semantic_checks",
        [],
    )

    model_checks = [
        check
        for check in model_checks
        if not check.get(
            "passed",
            False,
        )
        and check.get(
            "dimension"
        ) in {
            "Completeness",
            "Template Fidelity",
            "Hallucination Check",
        }
    ]

    guardrail_checks = _semantic_guardrail_checks(
        state
    )

    semantic_checks = _deduplicate_issues(
        model_checks
        + guardrail_checks
    )

    return {
        "semantic_checks": semantic_checks,
        "summary": result.get(
            "summary",
            "",
        ),
    }


# ============================================================================
# ISSUE DEDUPLICATION
# ============================================================================

def _deduplicate_issues(
    issues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Remove duplicate evaluation issues.
    """

    unique: list[dict[str, Any]] = []
    seen: set[tuple] = set()

    for issue in issues:

        key = (
            issue.get("dimension"),
            issue.get("issue"),
            issue.get("source_reference"),
            str(issue.get("expected")),
            str(issue.get("actual")),
            issue.get("evidence"),
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(issue)

    return unique


# ============================================================================
# SCORE CALCULATION
# ============================================================================

def _score_dimension(
    dimension: str,
    issues: list[dict[str, Any]],
) -> float:
    """
    Calculate a dimension score.

    Each independent issue applies a 15-point penalty.
    """

    issue_count = sum(
        1
        for issue in issues
        if issue.get(
            "dimension"
        ) == dimension
    )

    return max(
        0.0,
        100.0 - (
            15.0 * issue_count
        ),
    )


def _calculate_hybrid_scores(
    issues: list[dict[str, Any]],
) -> dict[str, float]:
    """
    Calculate all six evaluation dimensions.
    """

    return {
        dimension: _score_dimension(
            dimension,
            issues,
        )
        for dimension in EVALUATION_WEIGHTS
    }


def calculate_overall_score(
    dimension_scores: dict[str, float],
) -> float:
    """
    Calculate weighted overall evaluation score.
    """

    return round(
        sum(
            dimension_scores[dimension]
            * weight
            for dimension, weight
            in EVALUATION_WEIGHTS.items()
        ),
        2,
    )


# ============================================================================
# PUBLIC EVALUATOR
# ============================================================================

def evaluate_draft(
    state: AgentState,
) -> dict:
    """
    Run the complete hybrid evaluator.

    Pipeline:

        Generated Draft
              |
              +----------------------+
              |                      |
              v                      v
        Python checks          Qwen semantic checks
              |                      |
              |              semantic guardrails
              |                      |
              +----------+-----------+
                         |
                         v
                  Combined issues
                         |
                         v
                  Python scoring
                         |
                         v
                   Final report
    """

    deterministic_issues: list[
        dict[str, Any]
    ] = []

    # ------------------------------------------------------------------------
    # Objective Python checks
    # ------------------------------------------------------------------------

    deterministic_issues.extend(
        _deterministic_entity_checks(
            state
        )
    )

    deterministic_issues.extend(
        _deterministic_completeness_checks(
            state
        )
    )

    deterministic_issues.extend(
        _deterministic_structure_checks(
            state
        )
    )

    deterministic_issues.extend(
        _deterministic_consistency_checks(
            state
        )
    )

    deterministic_issues.extend(
        _deterministic_hallucination_checks(
            state
        )
    )

    # ------------------------------------------------------------------------
    # Semantic Qwen + high-confidence semantic guardrails
    # ------------------------------------------------------------------------

    semantic_result = _run_semantic_evaluation(
        state
    )

    semantic_issues = semantic_result[
        "semantic_checks"
    ]

    # ------------------------------------------------------------------------
    # Combine and deduplicate
    # ------------------------------------------------------------------------

    issues = _deduplicate_issues(
        deterministic_issues
        + semantic_issues
    )

    # ------------------------------------------------------------------------
    # Scores
    # ------------------------------------------------------------------------

    dimension_scores = _calculate_hybrid_scores(
        issues
    )

    overall_score = calculate_overall_score(
        dimension_scores
    )

    # ------------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------------

    summary = (
        f"Hybrid evaluation completed with "
        f"{len(deterministic_issues)} deterministic "
        f"issues and "
        f"{len(semantic_issues)} semantic issues."
    )

    return {
        "dimension_scores": dimension_scores,
        "overall_score": overall_score,
        "issues": issues,
        "deterministic_issues": deterministic_issues,
        "semantic_issues": semantic_issues,
        "semantic_summary": semantic_result[
            "summary"
        ],
        "summary": summary,
        "weights": dict(
            EVALUATION_WEIGHTS
        ),
        "model": MODEL_NAME,
    }