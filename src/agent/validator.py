from __future__ import annotations

from typing import Any

from src.agent.state import AgentState


# ============================================================================
# ERROR HANDLING
# ============================================================================

def _add_error(
    errors: list[dict[str, Any]],
    *,
    dimension: str,
    issue: str,
    source: str,
    expected: Any = None,
    actual: Any = None,
) -> None:
    error = {
        "dimension": dimension,
        "severity": "HIGH",
        "issue": issue,
        "source": source,
    }

    if expected is not None:
        error["expected"] = expected

    if actual is not None:
        error["actual"] = actual

    errors.append(error)


# ============================================================================
# DOCUMENT TYPE
# ============================================================================

def _check_document_type(
    draft: dict,
    state: AgentState,
    errors: list[dict[str, Any]],
) -> None:
    expected = state["case_data"].document_type.strip()
    actual = str(draft.get("document_type", "")).strip()

    if actual != expected:
        _add_error(
            errors,
            dimension="Entity Accuracy",
            issue="Document type does not match CaseData.",
            source="CaseData.document_type",
            expected=expected,
            actual=actual,
        )


# ============================================================================
# SECTION STRUCTURE
# ============================================================================

def _check_sections(
    draft: dict,
    state: AgentState,
    errors: list[dict[str, Any]],
) -> None:
    """
    Validate the ten logical TemplateSpecification sections against
    the actual representation used by the generated draft.
    """

    template = state["template_specification"]

    section_field_mapping = {
        "FORUM_HEADING": ("sections", "FORUM_HEADING"),
        "JURISDICTION": ("sections", "JURISDICTION"),
        "CASE_NUMBER": ("sections", "CASE_NUMBER"),
        "CAUSE_TITLE": ("sections", "CAUSE_TITLE"),
        "AFFIDAVIT_TITLE": ("sections", "AFFIDAVIT_TITLE"),
        "DEPONENT_CLAUSE": ("sections", "DEPONENT_CLAUSE"),
        "NUMBERED_PARAGRAPHS": ("paragraphs", None),
        "PRAYER": ("prayer", None),
        "JURAT": ("jurat", None),
        "VERIFICATION": ("verification", None),
    }

    for section in template.sections:
        if not section.required:
            continue

        mapping = section_field_mapping.get(section.name)

        if mapping is None:
            _add_error(
                errors,
                dimension="Structure",
                issue=(
                    f"Template section '{section.name}' has no "
                    "draft representation mapping."
                ),
                source="TemplateSpecification.sections",
                expected=section.name,
                actual=None,
            )
            continue

        field_name, nested_key = mapping

        # ------------------------------------------------------------------
        # Sections represented inside draft["sections"]
        # ------------------------------------------------------------------

        if field_name == "sections":
            sections = draft.get("sections")

            if not isinstance(sections, dict):
                _add_error(
                    errors,
                    dimension="Structure",
                    issue="Draft sections must be a JSON object.",
                    source="GeneratedDraft.sections",
                    expected="object",
                    actual=type(sections).__name__,
                )
                continue

            value = sections.get(nested_key)

            if not isinstance(value, str) or not value.strip():
                _add_error(
                    errors,
                    dimension="Structure",
                    issue=f"Required section '{section.name}' is missing.",
                    source="TemplateSpecification.sections",
                    expected=section.name,
                    actual=None,
                )

        # ------------------------------------------------------------------
        # Numbered paragraphs
        # ------------------------------------------------------------------

        elif field_name == "paragraphs":
            paragraphs = draft.get("paragraphs")

            if not isinstance(paragraphs, list) or not paragraphs:
                _add_error(
                    errors,
                    dimension="Structure",
                    issue=f"Required section '{section.name}' is missing.",
                    source="TemplateSpecification.sections",
                    expected=section.name,
                    actual=None,
                )

        # ------------------------------------------------------------------
        # Dedicated fields
        # ------------------------------------------------------------------

        else:
            value = draft.get(field_name)

            if not isinstance(value, str) or not value.strip():
                _add_error(
                    errors,
                    dimension="Structure",
                    issue=f"Required section '{section.name}' is missing.",
                    source="TemplateSpecification.sections",
                    expected=section.name,
                    actual=None,
                )


# ============================================================================
# PARAGRAPHS
# ============================================================================

def _check_paragraphs(
    draft: dict,
    state: AgentState,
    errors: list[dict[str, Any]],
) -> None:
    content_map = state["content_map"]

    paragraphs = draft.get("paragraphs", [])

    if not isinstance(paragraphs, list):
        _add_error(
            errors,
            dimension="Structure",
            issue="Generated paragraphs must be a list.",
            source="GeneratedDraft.paragraphs",
            expected="list",
            actual=type(paragraphs).__name__,
        )
        return

    expected_count = content_map.paragraph_count
    actual_count = len(paragraphs)

    # ----------------------------------------------------------------------
    # Count
    # ----------------------------------------------------------------------

    if actual_count != expected_count:
        _add_error(
            errors,
            dimension="Completeness",
            issue="Generated paragraph count does not match ContentMap.",
            source="ContentMap.paragraph_count",
            expected=expected_count,
            actual=actual_count,
        )

    # ----------------------------------------------------------------------
    # Numbering
    # ----------------------------------------------------------------------

    expected_numbers = list(
        range(1, expected_count + 1)
    )

    actual_numbers = [
        paragraph.get("paragraph_number")
        if isinstance(paragraph, dict)
        else None
        for paragraph in paragraphs
    ]

    if actual_numbers != expected_numbers:
        _add_error(
            errors,
            dimension="Structure",
            issue="Generated paragraph numbering is not sequential.",
            source="ContentMap.paragraph_count",
            expected=expected_numbers,
            actual=actual_numbers,
        )

    # ----------------------------------------------------------------------
    # Content
    # ----------------------------------------------------------------------

    for index, paragraph in enumerate(paragraphs, start=1):
        if not isinstance(paragraph, dict):
            _add_error(
                errors,
                dimension="Completeness",
                issue=(
                    f"Paragraph {index} is not represented as an object."
                ),
                source="GeneratedDraft.paragraphs",
                expected="object",
                actual=type(paragraph).__name__,
            )
            continue

        content = paragraph.get("content")

        if not isinstance(content, str) or not content.strip():
            _add_error(
                errors,
                dimension="Completeness",
                issue=f"Paragraph {index} contains no substantive content.",
                source="GeneratedDraft.paragraphs",
                expected="non-empty paragraph content",
                actual=content,
            )


# ============================================================================
# CORE ENTITY VALIDATION
# ============================================================================

def _check_entities(
    draft: dict,
    state: AgentState,
    errors: list[dict[str, Any]],
) -> None:
    case = state["case_data"]
    sections = draft.get("sections", {})

    if not isinstance(sections, dict):
        return

    # ----------------------------------------------------------------------
    # Forum
    # ----------------------------------------------------------------------

    expected = case.court.strip()
    actual = str(
        sections.get("FORUM_HEADING", "")
    ).strip()

    if actual != expected:
        _add_error(
            errors,
            dimension="Entity Accuracy",
            issue=(
                "Forum heading does not exactly match CaseData."
            ),
            source="CaseData.court",
            expected=expected,
            actual=actual,
        )

    # ----------------------------------------------------------------------
    # Jurisdiction
    # ----------------------------------------------------------------------

    expected = case.jurisdiction.strip()
    actual = str(
        sections.get("JURISDICTION", "")
    ).strip()

    if actual != expected:
        _add_error(
            errors,
            dimension="Entity Accuracy",
            issue=(
                "Jurisdiction does not exactly match CaseData."
            ),
            source="CaseData.jurisdiction",
            expected=expected,
            actual=actual,
        )


# ============================================================================
# AFFIDAVIT TITLE
# ============================================================================

def _get_respondent_number(state: AgentState) -> str:
    """
    Extract the respondent number from CaseData.filed_on_behalf_of.

    Example:
        Respondent No. 2 -> 2
    """

    value = (
        state["case_data"].filed_on_behalf_of or ""
    ).strip()

    prefix = "Respondent No."

    if value.lower().startswith(prefix.lower()):
        return value[len(prefix):].strip()

    return ""


def _check_affidavit_title(
    draft: dict,
    state: AgentState,
    errors: list[dict[str, Any]],
) -> None:
    case = state["case_data"]
    sections = draft.get("sections", {})

    actual = str(
        sections.get("AFFIDAVIT_TITLE", "")
    ).strip()

    respondent_number = _get_respondent_number(state)

    if respondent_number:
        expected = (
            "AFFIDAVIT IN REPLY ON BEHALF OF "
            f"RESPONDENT NO. {respondent_number}"
        )
    else:
        expected = "AFFIDAVIT IN REPLY"

    if actual != expected:
        _add_error(
            errors,
            dimension="Template Fidelity",
            issue=(
                "Affidavit title does not follow the required "
                "template title."
            ),
            source=(
                "TemplateSpecification fixed title + "
                "CaseData.filed_on_behalf_of"
            ),
            expected=expected,
            actual=actual,
        )


# ============================================================================
# CASE NUMBER
# ============================================================================

def _check_case_number(
    draft: dict,
    state: AgentState,
    errors: list[dict[str, Any]],
) -> None:
    case = state["case_data"]
    sections = draft.get("sections", {})

    expected = (
        f"{case.proceeding_type.strip()} "
        f"No. {case.case_number.strip()} "
        f"of {case.year.strip()}"
    )

    actual = str(
        sections.get("CASE_NUMBER", "")
    ).strip()

    if actual != expected:
        _add_error(
            errors,
            dimension="Entity Accuracy",
            issue=(
                "Case number representation does not match "
                "the mapped case number."
            ),
            source=(
                "CaseData.proceeding_type + "
                "CaseData.case_number + CaseData.year"
            ),
            expected=expected,
            actual=actual,
        )


# ============================================================================
# CAUSE TITLE
# ============================================================================

def _check_cause_title(
    draft: dict,
    state: AgentState,
    errors: list[dict[str, Any]],
) -> None:
    case = state["case_data"]
    sections = draft.get("sections", {})

    actual = str(
        sections.get("CAUSE_TITLE", "")
    ).strip()

    expected_parties = [
        case.petitioner,
        *case.respondents.values(),
    ]

    for expected in expected_parties:
        expected = expected.strip()

        if expected and expected not in actual:
            _add_error(
                errors,
                dimension="Entity Accuracy",
                issue=(
                    "Cause title does not contain an expected "
                    f"party: {expected}."
                ),
                source=(
                    "CaseData.petitioner / "
                    "CaseData.respondents"
                ),
                expected=expected,
                actual=actual,
            )


# ============================================================================
# DEPONENT
# ============================================================================

def _check_deponent(
    draft: dict,
    state: AgentState,
    errors: list[dict[str, Any]],
) -> None:
    case = state["case_data"]
    sections = draft.get("sections", {})

    actual = str(
        sections.get("DEPONENT_CLAUSE", "")
    ).strip()

    expected_values = [
        case.deponent_name,
        case.designation,
        case.organisation,
        case.filed_on_behalf_of,
    ]

    for expected in expected_values:
        expected = expected.strip()

        if expected and expected not in actual:
            _add_error(
                errors,
                dimension="Entity Accuracy",
                issue=(
                    "Deponent clause does not contain expected "
                    f"information: {expected}."
                ),
                source=(
                    "CaseData.deponent_name / designation / "
                    "organisation / filed_on_behalf_of"
                ),
                expected=expected,
                actual=actual,
            )


# ============================================================================
# EXHIBIT
# ============================================================================

def _check_exhibit(
    draft: dict,
    state: AgentState,
    errors: list[dict[str, Any]],
) -> None:
    expected = (
        state["case_data"].exhibit or ""
    ).strip()

    actual = str(
        draft.get("exhibit", "")
    ).strip()

    if expected and actual != expected:
        _add_error(
            errors,
            dimension="Consistency",
            issue="Exhibit marker does not match CaseData.",
            source="CaseData.exhibit",
            expected=expected,
            actual=actual,
        )


# ============================================================================
# PRAYER
# ============================================================================

def _check_prayer(
    draft: dict,
    state: AgentState,
    errors: list[dict[str, Any]],
) -> None:
    expected = (
        state["case_data"].prayer or ""
    ).strip()

    actual = str(
        draft.get("prayer", "")
    ).strip()

    if expected and actual != expected:
        _add_error(
            errors,
            dimension="Completeness",
            issue="Prayer does not match the supplied case prayer.",
            source="CaseData.prayer",
            expected=expected,
            actual=actual,
        )


# ============================================================================
# JURAT
# ============================================================================

def _expected_jurat_verb(
    verification_verb: str,
) -> str:
    """
    Map the Part 6 verification verb to the corresponding Part 9
    jurat wording.
    """

    normalized = verification_verb.strip().lower()

    mapping = {
        "solemnly affirm": "Solemnly affirmed",
        "affirm": "Affirmed",
        "verify": "Verified",
    }

    return mapping.get(
        normalized,
        verification_verb.strip().capitalize(),
    )


def _check_jurat(
    draft: dict,
    state: AgentState,
    errors: list[dict[str, Any]],
) -> None:
    case = state["case_data"]

    actual = str(
        draft.get("jurat", "")
    ).strip()

    expected_verb = _expected_jurat_verb(
        case.verification_verb
    )

    if expected_verb and expected_verb not in actual:
        _add_error(
            errors,
            dimension="Consistency",
            issue=(
                "Jurat verb does not match the verification "
                "verb required by the template."
            ),
            source=(
                "CaseData.verification_verb + "
                "TemplateSpecification Part 9"
            ),
            expected=expected_verb,
            actual=actual,
        )

    expected_values = [
        case.deponent_name,
        case.attestation_place,
        case.attestation_date,
    ]

    for expected in expected_values:
        expected = expected.strip()

        if expected and expected not in actual:
            _add_error(
                errors,
                dimension="Consistency",
                issue=(
                    "Jurat does not contain expected information: "
                    f"{expected}."
                ),
                source=(
                    "CaseData.deponent_name / "
                    "attestation_place / attestation_date"
                ),
                expected=expected,
                actual=actual,
            )

    # Required structural markers from the reference.
    if "Before Me" not in actual:
        _add_error(
            errors,
            dimension="Template Fidelity",
            issue="Jurat is missing the 'Before Me' marker.",
            source="TemplateSpecification Part 9",
            expected="Before Me",
            actual=actual,
        )


# ============================================================================
# VERIFICATION
# ============================================================================

def _check_verification(
    draft: dict,
    state: AgentState,
    errors: list[dict[str, Any]],
) -> None:
    case = state["case_data"]
    content_map = state["content_map"]

    actual = str(
        draft.get("verification", "")
    ).strip()

    paragraph_count = content_map.paragraph_count

    # ----------------------------------------------------------------------
    # Required verification wording
    # ----------------------------------------------------------------------

    required_phrases = [
        "do hereby verify",
        "true and correct",
        "knowledge and belief",
        "nothing material has been concealed",
    ]

    for phrase in required_phrases:
        if phrase.lower() not in actual.lower():
            _add_error(
                errors,
                dimension="Template Fidelity",
                issue=(
                    "Verification is missing required wording: "
                    f"'{phrase}'."
                ),
                source="TemplateSpecification Part 10",
                expected=phrase,
                actual=actual,
            )

    # ----------------------------------------------------------------------
    # Paragraph range
    # ----------------------------------------------------------------------

    expected_range = (
        f"paragraphs 1 to {paragraph_count} "
        "and the Prayer"
    )

    if expected_range.lower() not in actual.lower():
        _add_error(
            errors,
            dimension="Consistency",
            issue=(
                "Verification paragraph range does not match "
                "the generated body count."
            ),
            source=(
                "TemplateSpecification consistency rule + "
                "ContentMap.paragraph_count"
            ),
            expected=expected_range,
            actual=actual,
        )

    # ----------------------------------------------------------------------
    # Deponent
    # ----------------------------------------------------------------------

    if case.deponent_name:
        if case.deponent_name.lower() not in actual.lower():
            _add_error(
                errors,
                dimension="Entity Accuracy",
                issue=(
                    "Verification does not contain the deponent's name."
                ),
                source="CaseData.deponent_name",
                expected=case.deponent_name,
                actual=actual,
            )

    # ----------------------------------------------------------------------
    # Place
    # ----------------------------------------------------------------------

    if case.attestation_place:
        if case.attestation_place.lower() not in actual.lower():
            _add_error(
                errors,
                dimension="Consistency",
                issue=(
                    "Verification does not contain the "
                    "attestation place."
                ),
                source="CaseData.attestation_place",
                expected=case.attestation_place,
                actual=actual,
            )

    # ----------------------------------------------------------------------
    # Date
    # ----------------------------------------------------------------------

    if case.attestation_date:
        if case.attestation_date.lower() not in actual.lower():
            _add_error(
                errors,
                dimension="Consistency",
                issue=(
                    "Verification does not contain the "
                    "attestation date."
                ),
                source="CaseData.attestation_date",
                expected=case.attestation_date,
                actual=actual,
            )


# ============================================================================
# ADVOCATE
# ============================================================================

def _check_advocate(
    draft: dict,
    state: AgentState,
    errors: list[dict[str, Any]],
) -> None:
    case = state["case_data"]

    actual = str(
        draft.get("advocate", "")
    ).strip()

    expected_values = [
        case.advocate_firm,
        case.advocate_for,
    ]

    for expected in expected_values:
        expected = expected.strip()

        if expected and expected not in actual:
            _add_error(
                errors,
                dimension="Completeness",
                issue=(
                    "Advocate block does not contain expected "
                    f"information: {expected}."
                ),
                source="CaseData.advocate_firm / advocate_for",
                expected=expected,
                actual=actual,
            )


# ============================================================================
# DETERMINISTIC TEMPLATE RULES
# ============================================================================

def _check_template_rules(
    draft: dict,
    state: AgentState,
    errors: list[dict[str, Any]],
) -> None:
    """
    Validate important template-specific rules that are not simple
    entity comparisons.
    """

    case = state["case_data"]
    sections = draft.get("sections", {})

    # ----------------------------------------------------------------------
    # Affidavit title
    # ----------------------------------------------------------------------

    title = str(
        sections.get("AFFIDAVIT_TITLE", "")
    ).strip()

    respondent_number = _get_respondent_number(state)

    if respondent_number:
        expected_title = (
            "AFFIDAVIT IN REPLY ON BEHALF OF "
            f"RESPONDENT NO. {respondent_number}"
        )

        if title != expected_title:
            _add_error(
                errors,
                dimension="Template Fidelity",
                issue=(
                    "Affidavit title does not identify the "
                    "correct respondent."
                ),
                source="TemplateSpecification Part 5",
                expected=expected_title,
                actual=title,
            )

    # ----------------------------------------------------------------------
    # Prayer must remain separate from numbered paragraphs
    # ----------------------------------------------------------------------



# ============================================================================
# DIMENSION SCORING
# ============================================================================

def _calculate_dimension_scores(
    errors: list[dict[str, Any]],
) -> dict[str, float]:
    """
    Calculate deterministic scores.

    Each detected error deducts 10 points from its associated
    dimension, with a floor of 0.
    """

    dimensions = {
        "Entity Accuracy": 100.0,
        "Completeness": 100.0,
        "Structure": 100.0,
        "Consistency": 100.0,
        "Template Fidelity": 100.0,
        "Hallucination Check": 100.0,
    }

    for error in errors:
        dimension = error["dimension"]

        if dimension in dimensions:
            dimensions[dimension] = max(
                0.0,
                dimensions[dimension] - 10.0,
            )

    return dimensions


# ============================================================================
# MAIN VALIDATOR
# ============================================================================

def validate_draft(
    draft: dict,
    state: AgentState,
) -> dict:
    """
    Run deterministic validation against:

    - CaseData
    - TemplateSpecification
    - ContentMap

    No LLM is used.
    """

    errors: list[dict[str, Any]] = []

    # ----------------------------------------------------------------------
    # Basic document checks
    # ----------------------------------------------------------------------

    if not isinstance(draft, dict):
        _add_error(
            errors,
            dimension="Structure",
            issue="Generated draft must be a dictionary/object.",
            source="GeneratedDraft",
            expected="object",
            actual=type(draft).__name__,
        )

        scores = _calculate_dimension_scores(errors)

        return {
            "passed": False,
            "score": (
                sum(scores.values()) / len(scores)
            ),
            "dimension_scores": scores,
            "errors": errors,
            "warnings": [],
            "error_count": len(errors),
        }

    _check_document_type(
        draft,
        state,
        errors,
    )

    _check_sections(
        draft,
        state,
        errors,
    )

    _check_paragraphs(
        draft,
        state,
        errors,
    )

    _check_entities(
        draft,
        state,
        errors,
    )

    _check_affidavit_title(
        draft,
        state,
        errors,
    )

    _check_case_number(
        draft,
        state,
        errors,
    )

    _check_cause_title(
        draft,
        state,
        errors,
    )

    _check_deponent(
        draft,
        state,
        errors,
    )

    _check_exhibit(
        draft,
        state,
        errors,
    )

    _check_prayer(
        draft,
        state,
        errors,
    )

    _check_jurat(
        draft,
        state,
        errors,
    )

    _check_verification(
        draft,
        state,
        errors,
    )

    _check_advocate(
        draft,
        state,
        errors,
    )

    _check_template_rules(
        draft,
        state,
        errors,
    )

    # ----------------------------------------------------------------------
    # Deduplicate identical errors
    # ----------------------------------------------------------------------

    unique_errors: list[dict[str, Any]] = []
    seen: set[tuple] = set()

    for error in errors:
        key = (
            error.get("dimension"),
            error.get("issue"),
            error.get("source"),
            str(error.get("expected")),
            str(error.get("actual")),
        )

        if key not in seen:
            seen.add(key)
            unique_errors.append(error)

    errors = unique_errors

    # ----------------------------------------------------------------------
    # Scores
    # ----------------------------------------------------------------------

    scores = _calculate_dimension_scores(errors)

    passed = not errors

    return {
        "passed": passed,
        "score": (
            sum(scores.values()) / len(scores)
            if scores
            else 0.0
        ),
        "dimension_scores": scores,
        "errors": errors,
        "warnings": [],
        "error_count": len(errors),
    }


# ============================================================================
# LANGGRAPH VALIDATION NODE
# ============================================================================

def validation_node(
    state: AgentState,
) -> dict:
    """
    LangGraph node for deterministic validation.
    """

    draft = state.get("generated_draft")

    if not draft:
        results = {
            "passed": False,
            "score": 0.0,
            "dimension_scores": {},
            "errors": [
                {
                    "dimension": "Structure",
                    "severity": "HIGH",
                    "issue": "No generated draft is available.",
                    "source": "AgentState.generated_draft",
                }
            ],
            "warnings": [],
            "error_count": 1,
        }

        return {
            "validation_results": results,
            "status": "validation_failed",
        }

    results = validate_draft(
        draft,
        state,
    )

    return {
        "validation_results": results,
        "status": (
            "validation_passed"
            if results["passed"]
            else "validation_failed"
        ),
    }