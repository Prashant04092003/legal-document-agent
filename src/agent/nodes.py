from __future__ import annotations

import json

from langchain_ollama import ChatOllama

from src.agent.state import AgentState


# ============================================================================
# MODEL CONFIGURATION
# ============================================================================

MODEL_CONFIG = {
    "drafting": "qwen2.5:7b",
    "evaluation": "qwen2.5:7b",
    "revision": "qwen2.5:7b",
}


# ============================================================================
# DRAFT SCHEMA
# ============================================================================

DRAFT_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "document_type": {
            "type": "string",
        },
        "paragraphs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "paragraph_number": {
                        "type": "integer",
                    },
                    "content": {
                        "type": "string",
                    },
                },
                "required": [
                    "paragraph_number",
                    "content",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "document_type",
        "paragraphs",
    ],
    "additionalProperties": False,
}


# ============================================================================
# PHASE 4D — REVISION SCHEMA
# ============================================================================

REVISION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "document_type": {
            "type": "string",
        },
        "paragraphs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "paragraph_number": {
                        "type": "integer",
                    },
                    "content": {
                        "type": "string",
                    },
                },
                "required": [
                    "paragraph_number",
                    "content",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "document_type",
        "paragraphs",
    ],
    "additionalProperties": False,
}


# ============================================================================
# DRAFTING INSTRUCTIONS
# ============================================================================

DRAFTING_SYSTEM_INSTRUCTIONS = """
You are the substantive drafting component of an AI agent that generates
an Affidavit in Reply.

Your job is ONLY to draft the substantive content of the numbered
paragraphs.

The surrounding legal document structure will be constructed
deterministically by Python. Therefore, DO NOT generate headings,
titles, prayer, jurat, verification, exhibit blocks, advocate blocks,
or other structural sections.

STRICT RULES:

1. Use ONLY information supplied in the structured input.

2. Do NOT invent facts, dates, parties, documents, allegations,
   authorities, legal provisions, evidence, investigations, approvals,
   inspections, communications, or procedural events.

3. Preserve every supplied reply point.

4. Do not omit a supplied reply point.

5. Do not merge separate supplied reply points.

6. Generate exactly one numbered paragraph for every paragraph in
   ContentMap.

7. Preserve the paragraph numbers supplied by ContentMap.

8. The paragraph content must faithfully express the corresponding
   ContentMap content.

9. Preserve the substantive meaning of the source content. You may
   improve grammar, sentence flow, and legal drafting style, but
   you must not introduce new factual meaning.

10. The first paragraph must perform the supplied identity/perusal
    function.

11. The second paragraph must perform the supplied blanket-denial
    function.

12. Subsequent paragraphs must follow the supplied template move and
    source content.

13. The closing paragraph must express the supplied CLOSING move and
    source content.

14. Do not create a new legal argument that is not present in the
    structured input.

15. Do not add statutes, case law, authorities, legal provisions,
    evidence, or procedural facts.

16. If the source says that an action was taken according to an
    applicable redevelopment procedure, preserve that meaning.
    Do not replace it with a more specific procedure that is not
    supplied.

17. If the source identifies a communication and its date, preserve
    the communication and date exactly.

18. If the source identifies an exhibit, preserve the exhibit
    reference exactly.

19. Avoid unnecessary repetition.

20. Every paragraph must contain substantive non-empty content.

21. Return ONLY the structured JSON object required by the schema.

22. Do not return markdown, explanations, commentary, headings,
    or code fences.
"""


# ============================================================================
# PHASE 4D — REVISION INSTRUCTIONS
# ============================================================================

REVISION_SYSTEM_INSTRUCTIONS = """
You are the revision component of an AI agent generating an
Affidavit in Reply.

The affidavit has already been drafted and evaluated.

Your job is ONLY to revise the substantive content of the numbered
paragraphs in response to the supplied evaluation feedback.

Python will reconstruct all deterministic legal/template sections.

Therefore you MUST NOT generate or modify:

- forum heading
- jurisdiction
- case number
- cause title
- affidavit title
- deponent clause
- exhibit
- prayer
- jurat
- verification
- advocate block

You may ONLY modify:

- numbered paragraph content

============================================================
REVISION RULES
============================================================

1. Use ONLY information supplied in CaseData and ContentMap.

2. Do NOT invent facts, dates, parties, documents, allegations,
   authorities, legal provisions, evidence, investigations,
   approvals, inspections, communications, meetings, or procedural
   events.

3. Read every evaluation issue before revising.

4. Fix the specific problems identified by the evaluator.

5. Do NOT rewrite correct paragraphs unnecessarily.

6. Preserve paragraphs that are already semantically correct.

7. Preserve the paragraph numbers exactly.

8. Generate exactly the same number of paragraphs as ContentMap.

9. Every ContentMap paragraph must remain represented.

10. Preserve the substantive meaning of every mapped source point.

11. If an evaluation issue says that a paragraph is too generic,
    restore the material source content rather than merely changing
    the wording.

12. If an evaluation issue identifies an unsupported factual
    assertion, remove that assertion unless it is actually supported
    by CaseData or ContentMap.

13. Do not respond to an evaluator issue by adding a new fact.

14. Preserve the assigned template/reply move for every paragraph.

15. Paragraph 1 must perform the identity/perusal function.

16. Paragraph 2 must perform the blanket-denial function.

17. Subsequent paragraphs must perform their assigned ContentMap
    template moves.

18. The closing paragraph must preserve the supplied closing
    position.

19. Reasonable legal paraphrasing is allowed.

20. Do not copy evaluator commentary into the affidavit.

21. Do not add explanations outside the required JSON.

22. Return ONLY the structured JSON object required by the schema.
"""


# ============================================================================
# SERIALIZATION
# ============================================================================

def _serialize_case_data(state: AgentState) -> dict:
    case = state["case_data"]

    return {
        "document_type": case.document_type,
        "court": case.court,
        "jurisdiction": case.jurisdiction,
        "proceeding_type": case.proceeding_type,
        "case_number": case.case_number,
        "year": case.year,
        "petitioner": case.petitioner,
        "respondents": case.respondents,
        "filed_on_behalf_of": case.filed_on_behalf_of,
        "deponent_name": case.deponent_name,
        "designation": case.designation,
        "organisation": case.organisation,
        "address": case.address,
        "verification_verb": case.verification_verb,
        "reply_points": [
            {
                "number": point.number,
                "title": point.title,
                "content": point.content,
            }
            for point in case.reply_points
        ],
        "prayer": case.prayer,
        "exhibit": case.exhibit,
        "attestation_place": case.attestation_place,
        "attestation_date": case.attestation_date,
        "advocate_firm": case.advocate_firm,
        "advocate_for": case.advocate_for,
    }


def _serialize_template_specification(state: AgentState) -> dict:
    template = state["template_specification"]

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


def _serialize_content_map(state: AgentState) -> dict:
    content_map = state["content_map"]

    def serialize_mapping(mapping):
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
            {
                "target": mapping.target,
                "source": mapping.source,
                "value": mapping.value,
                "template_rule": mapping.template_rule,
            }
            for mapping in content_map.sections
        ],

        "paragraphs": [
            {
                "paragraph_number": paragraph.paragraph_number,
                "source_type": paragraph.source_type,
                "source_reference": paragraph.source_reference,
                "title": paragraph.title,
                "content": paragraph.content,
                "template_move": paragraph.template_move,
            }
            for paragraph in content_map.paragraphs
        ],

        "exhibit": serialize_mapping(content_map.exhibit),
        "prayer": serialize_mapping(content_map.prayer),
        "jurat": serialize_mapping(content_map.jurat),
        "verification": serialize_mapping(content_map.verification),
        "advocate": serialize_mapping(content_map.advocate),

        "paragraph_count": content_map.paragraph_count,
    }


# ============================================================================
# DETERMINISTIC TEMPLATE HELPERS
# ============================================================================

def _get_section_value(
    state: AgentState,
    section_name: str,
) -> str:
    """
    Retrieve a deterministic section value from ContentMap.
    """

    content_map = state["content_map"]

    for mapping in content_map.sections:
        if mapping.target == section_name:
            return mapping.value.strip()

    return ""


def _get_respondent_number(state: AgentState) -> str:
    """
    Determine the respondent number from filed_on_behalf_of.

    Example:
        'Respondent No. 2' -> '2'
    """

    case = state["case_data"]

    value = (case.filed_on_behalf_of or "").strip()

    prefix = "Respondent No."

    if value.lower().startswith(prefix.lower()):
        return value[len(prefix):].strip()

    deponent_clause = _get_section_value(
        state,
        "DEPONENT_CLAUSE",
    )

    marker = "Respondent No."

    lower_clause = deponent_clause.lower()
    marker_index = lower_clause.rfind(marker.lower())

    if marker_index >= 0:
        number = deponent_clause[
            marker_index + len(marker):
        ].strip()

        if number:
            return number.split()[0]

    return ""


def _build_forum_heading(state: AgentState) -> str:
    case = state["case_data"]

    city = ""

    forum_value = _get_section_value(
        state,
        "FORUM_HEADING",
    )

    if forum_value:
        return forum_value

    court = (case.court or "").strip()

    if "AT " in court:
        city = court.split("AT ", 1)[1].strip()

    if city:
        return (
            "IN THE HIGH COURT OF JUDICATURE AT "
            + city
        )

    return court


def _build_jurisdiction(state: AgentState) -> str:
    value = _get_section_value(
        state,
        "JURISDICTION",
    )

    if value:
        return value

    return state["case_data"].jurisdiction.strip()


def _build_case_number(state: AgentState) -> str:
    case = state["case_data"]

    proceeding_type = case.proceeding_type.strip()
    case_number = case.case_number.strip()
    year = case.year.strip()

    return (
        f"{proceeding_type} No. "
        f"{case_number} of {year}"
    )


def _build_cause_title(state: AgentState) -> str:
    case = state["case_data"]

    petitioner = case.petitioner.strip()

    respondent_values = [
        value.strip()
        for _, value in sorted(
            case.respondents.items(),
            key=lambda item: item[0],
        )
        if value.strip()
    ]

    if not respondent_values:
        return petitioner

    if len(respondent_values) == 1:
        respondents = respondent_values[0]
    elif len(respondent_values) == 2:
        respondents = (
            f"{respondent_values[0]} and "
            f"{respondent_values[1]}"
        )
    else:
        respondents = ", ".join(
            respondent_values[:-1]
        ) + f", and {respondent_values[-1]}"

    return f"{petitioner} vs. {respondents}"


def _build_affidavit_title(state: AgentState) -> str:
    respondent_number = _get_respondent_number(state)

    if respondent_number:
        return (
            "AFFIDAVIT IN REPLY ON BEHALF OF "
            f"RESPONDENT NO. {respondent_number}"
        )

    return "AFFIDAVIT IN REPLY"


def _build_deponent_clause(state: AgentState) -> str:
    case = state["case_data"]

    name = case.deponent_name.strip()
    designation = case.designation.strip()
    organisation = case.organisation.strip()
    address = case.address.strip()
    respondent_number = _get_respondent_number(state)

    parts = [
        value
        for value in [
            name,
            designation,
            organisation,
            address,
        ]
        if value
    ]

    clause = ", ".join(parts)

    if respondent_number:
        if clause:
            clause += ", "

        clause += (
            f"Respondent No. {respondent_number}"
        )

    return clause


def _build_exhibit(state: AgentState) -> str:
    case = state["case_data"]

    return (case.exhibit or "").strip()


def _build_prayer(state: AgentState) -> str:
    case = state["case_data"]

    prayer = (case.prayer or "").strip()

    if prayer:
        return prayer

    mapping = state["content_map"].prayer

    if mapping is not None:
        return mapping.value.strip()

    return ""


def _verb_to_jurat_phrase(verification_verb: str) -> str:
    """
    Convert the Part 6 verification verb into the corresponding
    jurat phrase required by the reference structure.
    """

    verb = verification_verb.strip().lower()

    mapping = {
        "solemnly affirm": "Solemnly affirmed",
        "affirm": "Affirmed",
        "verify": "Verified",
    }

    return mapping.get(
        verb,
        verification_verb.strip().capitalize(),
    )


def _build_jurat(state: AgentState) -> str:
    case = state["case_data"]

    verb = _verb_to_jurat_phrase(
        case.verification_verb
    )

    place = case.attestation_place.strip()
    date = case.attestation_date.strip()
    name = case.deponent_name.strip()

    lines = []

    if place:
        lines.append(
            f"{verb} at {place}"
        )
    else:
        lines.append(verb)

    if date:
        lines.append(
            f"On this {date}"
        )

    lines.extend([
        "",
        name,
        "",
        "Before Me",
    ])

    return "\n".join(lines)


def _build_verification(state: AgentState) -> str:
    case = state["case_data"]
    content_map = state["content_map"]

    paragraph_count = content_map.paragraph_count
    name = case.deponent_name.strip()
    place = case.attestation_place.strip()
    date = case.attestation_date.strip()

    lines = [
        "VERIFICATION",
        "",
        (
            f"I, {name}, the Deponent above named, do hereby "
            f"verify that the contents of paragraphs 1 to "
            f"{paragraph_count} and the Prayer above are true "
            "and correct to my knowledge and belief and that "
            "nothing material has been concealed therefrom."
        ),
    ]

    if place and date:
        lines.extend([
            "",
            f"Verified at {place} on this {date}",
        ])
    elif place:
        lines.extend([
            "",
            f"Verified at {place}",
        ])
    elif date:
        lines.extend([
            "",
            f"Verified on this {date}",
        ])

    lines.extend([
        "",
        "DEPONENT",
    ])

    return "\n".join(lines)


def _build_advocate(state: AgentState) -> str:
    case = state["case_data"]

    firm = case.advocate_firm.strip()
    advocate_for = case.advocate_for.strip()

    if firm and advocate_for:
        return f"{firm}; {advocate_for}"

    return firm or advocate_for


def _assemble_draft(
    state: AgentState,
    generated_paragraphs: list[dict],
) -> dict:
    """
    Construct the complete affidavit draft.

    All deterministic legal/template-sensitive fields are generated here
    rather than delegated to the language model.
    """

    case = state["case_data"]

    return {
        "document_type": case.document_type,

        "sections": {
            "FORUM_HEADING": _build_forum_heading(state),
            "JURISDICTION": _build_jurisdiction(state),
            "CASE_NUMBER": _build_case_number(state),
            "CAUSE_TITLE": _build_cause_title(state),
            "AFFIDAVIT_TITLE": _build_affidavit_title(state),
            "DEPONENT_CLAUSE": _build_deponent_clause(state),
        },

        "paragraphs": generated_paragraphs,

        "exhibit": _build_exhibit(state),
        "prayer": _build_prayer(state),
        "jurat": _build_jurat(state),
        "verification": _build_verification(state),
        "advocate": _build_advocate(state),
    }


# ============================================================================
# PROMPT CONSTRUCTION
# ============================================================================

def build_drafting_prompt(state: AgentState) -> str:
    payload = {
        "case_data": _serialize_case_data(state),
        "template_specification": _serialize_template_specification(state),
        "content_map": _serialize_content_map(state),
        "drafting_scope": {
            "model_must_generate": [
                "NUMBERED_PARAGRAPHS"
            ],
            "model_must_not_generate": [
                "FORUM_HEADING",
                "JURISDICTION",
                "CASE_NUMBER",
                "CAUSE_TITLE",
                "AFFIDAVIT_TITLE",
                "DEPONENT_CLAUSE",
                "EXHIBIT",
                "PRAYER",
                "JURAT",
                "VERIFICATION",
                "ADVOCATE",
            ],
        },
    }

    return (
        DRAFTING_SYSTEM_INSTRUCTIONS
        + "\n\nSTRUCTURED INPUT:\n"
        + json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
    )


# ============================================================================
# PHASE 4D — REVISION PROMPT
# ============================================================================

def build_revision_prompt(state: AgentState) -> str:
    """
    Build the prompt for the Phase 4D revision agent.

    The model receives the complete current draft and evaluation
    findings, but is explicitly restricted to substantive numbered
    paragraph revision.
    """

    payload = {
        "case_data": _serialize_case_data(state),
        "template_specification": _serialize_template_specification(state),
        "content_map": _serialize_content_map(state),
        "current_draft": state["generated_draft"],
        "evaluation_results": state.get(
            "evaluation_results",
            {},
        ),
        "revision_scope": {
            "model_may_modify": [
                "NUMBERED_PARAGRAPHS"
            ],
            "model_must_not_modify": [
                "FORUM_HEADING",
                "JURISDICTION",
                "CASE_NUMBER",
                "CAUSE_TITLE",
                "AFFIDAVIT_TITLE",
                "DEPONENT_CLAUSE",
                "EXHIBIT",
                "PRAYER",
                "JURAT",
                "VERIFICATION",
                "ADVOCATE",
            ],
        },
    }

    return (
        REVISION_SYSTEM_INSTRUCTIONS
        + "\n\nSTRUCTURED REVISION INPUT:\n"
        + json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
    )


# ============================================================================
# RESPONSE VALIDATION
# ============================================================================

def _validate_model_paragraphs(
    response: dict,
    state: AgentState,
) -> None:
    if not isinstance(response, dict):
        raise ValueError(
            "The drafting model returned a non-object response."
        )

    required_keys = {
        "document_type",
        "paragraphs",
    }

    missing = required_keys - set(response)

    if missing:
        raise ValueError(
            "Drafting model response is missing required fields: "
            + ", ".join(sorted(missing))
        )

    case = state["case_data"]
    content_map = state["content_map"]

    if response["document_type"] != case.document_type:
        raise ValueError(
            "Drafting model document type does not match CaseData."
        )

    paragraphs = response["paragraphs"]

    if not isinstance(paragraphs, list):
        raise ValueError(
            "Drafting model paragraphs must be a JSON array."
        )

    expected_count = content_map.paragraph_count

    if len(paragraphs) != expected_count:
        raise ValueError(
            "Generated paragraph count does not match ContentMap. "
            f"Expected {expected_count}, got {len(paragraphs)}."
        )

    expected_numbers = list(
        range(1, expected_count + 1)
    )

    actual_numbers = [
        paragraph.get("paragraph_number")
        for paragraph in paragraphs
    ]

    if actual_numbers != expected_numbers:
        raise ValueError(
            "Generated paragraph numbering is invalid. "
            f"Expected {expected_numbers}, got {actual_numbers}."
        )

    for paragraph in paragraphs:
        if not isinstance(paragraph, dict):
            raise ValueError(
                "Every generated paragraph must be an object."
            )

        content = paragraph.get("content")

        if not isinstance(content, str):
            raise ValueError(
                "Every generated paragraph content must be a string."
            )

        if not content.strip():
            raise ValueError(
                "Every generated paragraph must contain "
                "non-empty content."
            )


# ============================================================================
# PHASE 4D — REVISION RESPONSE VALIDATION
# ============================================================================

def _validate_revision_response(
    response: dict,
    state: AgentState,
) -> None:
    """
    Validate the revision agent response.

    Revision is deliberately restricted to substantive paragraphs.
    """

    if not isinstance(response, dict):
        raise ValueError(
            "The revision model returned a non-object response."
        )

    required_keys = {
        "document_type",
        "paragraphs",
    }

    missing = required_keys - set(response)

    if missing:
        raise ValueError(
            "Revision model response is missing required fields: "
            + ", ".join(sorted(missing))
        )

    case = state["case_data"]
    content_map = state["content_map"]

    if response["document_type"] != case.document_type:
        raise ValueError(
            "Revision model document type does not match CaseData."
        )

    paragraphs = response["paragraphs"]

    if not isinstance(
        paragraphs,
        list,
    ):
        raise ValueError(
            "Revision model paragraphs must be a JSON array."
        )

    expected_count = content_map.paragraph_count

    if len(paragraphs) != expected_count:
        raise ValueError(
            "Revision model changed the paragraph count. "
            f"Expected {expected_count}, got {len(paragraphs)}."
        )

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
        raise ValueError(
            "Revision model changed paragraph numbering. "
            f"Expected {expected_numbers}, got {actual_numbers}."
        )

    for paragraph in paragraphs:

        if not isinstance(
            paragraph,
            dict,
        ):
            raise ValueError(
                "Every revised paragraph must be an object."
            )

        content = paragraph.get(
            "content"
        )

        if not isinstance(
            content,
            str,
        ):
            raise ValueError(
                "Every revised paragraph content must be a string."
            )

        if not content.strip():
            raise ValueError(
                "Every revised paragraph must contain "
                "non-empty content."
            )


# ============================================================================
# DETERMINISTIC STRUCTURAL VALIDATION
# ============================================================================

def _validate_assembled_draft(
    draft: dict,
    state: AgentState,
) -> None:
    """
    Validate the complete draft after deterministic assembly.

    This is intentionally stricter than validating the raw LLM output.
    """

    required_keys = {
        "document_type",
        "sections",
        "paragraphs",
        "exhibit",
        "prayer",
        "jurat",
        "verification",
        "advocate",
    }

    missing = required_keys - set(draft)

    if missing:
        raise ValueError(
            "Assembled draft is missing required fields: "
            + ", ".join(sorted(missing))
        )

    sections = draft["sections"]

    required_sections = {
        "FORUM_HEADING",
        "JURISDICTION",
        "CASE_NUMBER",
        "CAUSE_TITLE",
        "AFFIDAVIT_TITLE",
        "DEPONENT_CLAUSE",
    }

    missing_sections = (
        required_sections - set(sections)
    )

    if missing_sections:
        raise ValueError(
            "Assembled draft is missing sections: "
            + ", ".join(sorted(missing_sections))
        )

    for section_name in required_sections:
        value = sections.get(section_name)

        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Required section '{section_name}' is empty."
            )

    paragraphs = draft["paragraphs"]

    if not isinstance(paragraphs, list):
        raise ValueError(
            "Assembled draft paragraphs must be a JSON array."
        )

    expected_count = state["content_map"].paragraph_count

    if len(paragraphs) != expected_count:
        raise ValueError(
            "Assembled draft paragraph count is incorrect. "
            f"Expected {expected_count}, got {len(paragraphs)}."
        )

    expected_numbers = list(
        range(1, expected_count + 1)
    )

    actual_numbers = [
        paragraph.get("paragraph_number")
        for paragraph in paragraphs
    ]

    if actual_numbers != expected_numbers:
        raise ValueError(
            "Assembled draft paragraph numbering is invalid."
        )

    for paragraph in paragraphs:
        if not paragraph.get("content", "").strip():
            raise ValueError(
                "Assembled draft contains an empty paragraph."
            )

    if not draft["prayer"].strip():
        raise ValueError(
            "Prayer cannot be empty."
        )

    if not draft["jurat"].strip():
        raise ValueError(
            "Jurat cannot be empty."
        )

    if not draft["verification"].strip():
        raise ValueError(
            "Verification cannot be empty."
        )


# ============================================================================
# BACKWARD-COMPATIBLE RESPONSE VALIDATION
# ============================================================================

def _validate_draft_response(
    draft: dict,
    state: AgentState,
) -> None:
    """
    Validate a complete draft.

    Kept as a public-in-module compatibility function because the
    existing tests and graph may call it directly.
    """

    _validate_assembled_draft(
        draft,
        state,
    )


# ============================================================================
# DRAFTING AGENT NODE
# ============================================================================

def drafting_agent_node(state: AgentState) -> dict:
    """
    LangGraph drafting-agent node.

    Qwen is used for substantive paragraph drafting only.

    Python deterministically constructs all legal/template-sensitive
    fields so that structural correctness does not depend on LLM
    formatting behaviour.
    """

    prompt = build_drafting_prompt(state)

    model = ChatOllama(
        model=MODEL_CONFIG["drafting"],
        temperature=0,
    )

    structured_model = model.with_structured_output(
        DRAFT_JSON_SCHEMA,
        method="json_schema",
    )

    model_response = structured_model.invoke(prompt)

    _validate_model_paragraphs(
        model_response,
        state,
    )

    final_draft = _assemble_draft(
        state,
        model_response["paragraphs"],
    )

    _validate_assembled_draft(
        final_draft,
        state,
    )

    return {
        "generated_draft": final_draft,
        "status": "draft_generated",
        "error": "",
    }


# ============================================================================
# EVALUATION AGENT NODE
# ============================================================================

def evaluation_agent_node(state: AgentState) -> dict:
    """
    Evaluate the generated affidavit semantically using the
    local evaluation model.
    """

    from src.evaluation.evaluator import evaluate_draft

    evaluation_results = evaluate_draft(state)

    return {
        "evaluation_results": evaluation_results,
        "status": "evaluation_completed",
    }


# ============================================================================
# PHASE 4D — REVISION AGENT NODE
# ============================================================================

def revision_agent_node(state: AgentState) -> dict:
    """
    Revise the substantive numbered paragraphs using evaluation
    feedback.

    Only paragraph content comes from Qwen.

    All deterministic affidavit sections are reconstructed by
    _assemble_draft(), preventing the revision model from changing
    case number, party identity, jurat, verification, prayer, etc.
    """

    current_draft = state.get(
        "generated_draft"
    )

    if not isinstance(
        current_draft,
        dict,
    ):
        raise ValueError(
            "Revision cannot run without a generated draft."
        )

    evaluation_results = state.get(
        "evaluation_results"
    )

    if not isinstance(
        evaluation_results,
        dict,
    ):
        raise ValueError(
            "Revision cannot run without evaluation results."
        )

    prompt = build_revision_prompt(state)

    model = ChatOllama(
        model=MODEL_CONFIG["revision"],
        temperature=0,
    )

    structured_model = model.with_structured_output(
        REVISION_JSON_SCHEMA,
        method="json_schema",
    )

    model_response = structured_model.invoke(
        prompt
    )

    _validate_revision_response(
        model_response,
        state,
    )

    revised_draft = _assemble_draft(
        state,
        model_response["paragraphs"],
    )

    _validate_assembled_draft(
        revised_draft,
        state,
    )

    previous_revision_count = state.get(
        "revision_count",
        0,
    )

    evaluation_history = list(
        state.get(
            "evaluation_history",
            [],
        )
    )

    evaluation_history.append(
        evaluation_results
    )

    return {
        "generated_draft": revised_draft,
        "revision_count": previous_revision_count + 1,
        "evaluation_history": evaluation_history,
        "status": "draft_revised",
        "error": "",
    }