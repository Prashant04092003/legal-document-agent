from copy import deepcopy
from pathlib import Path

from src.agent.graph import MAX_REVISIONS, should_revise
from src.agent.nodes import (
    evaluation_agent_node,
    revision_agent_node,
)
from src.agent.validator import validation_node
from src.evaluation.evaluator import evaluate_draft
from src.extraction.entity_extractor import extract_case_data
from src.extraction.pdf_extractor import extract_pdf_text
from src.mapping.content_mapper import build_content_map
from src.template.template_analyzer import (
    analyze_reference_documents,
    build_template_specification,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

FORMAT_EXPLAINED = (
    PROJECT_ROOT
    / "data"
    / "reference"
    / "01 Affidavit Format Explained.pdf"
)

SAMPLE_AFFIDAVIT = (
    PROJECT_ROOT
    / "data"
    / "reference"
    / "02 Affidavit in Reply Sample.docx.pdf"
)

CASE_INFORMATION = (
    PROJECT_ROOT
    / "data"
    / "input"
    / "03_Case_Information.pdf"
)


def _build_phase4_inputs():
    """Build the exact real inputs used by the existing Phase 4 test."""

    template_knowledge = analyze_reference_documents(
        str(FORMAT_EXPLAINED),
        str(SAMPLE_AFFIDAVIT),
    )

    template_specification = build_template_specification(
        template_knowledge
    )

    case_pages = extract_pdf_text(
        CASE_INFORMATION
    )

    case_data = extract_case_data(
        case_pages
    )

    content_map = build_content_map(
        case_data,
        template_specification,
    )

    return (
        case_data,
        template_specification,
        content_map,
    )


def _corrupt_draft(draft):
    """
    Apply the same adversarial corruptions already established
    in Phase 4C.1.
    """

    corrupted_draft = deepcopy(draft)

    # --------------------------------------------------------------
    # Corruption 1: wrong case number
    # --------------------------------------------------------------

    corrupted_draft["sections"]["CASE_NUMBER"] = (
        "WRIT PETITION No. 9999 of 2026"
    )

    # --------------------------------------------------------------
    # Corruption 2: weaken a materially specific substantive reply
    # --------------------------------------------------------------

    if len(corrupted_draft["paragraphs"]) >= 4:
        corrupted_draft["paragraphs"][3]["content"] = (
            "With reference to the Petition, I deny the allegations."
        )

    # --------------------------------------------------------------
    # Corruption 3: wrong verification paragraph range
    # --------------------------------------------------------------

    corrupted_draft["verification"] = (
        corrupted_draft["verification"]
        .replace(
            "paragraphs 1 to 7",
            "paragraphs 1 to 5",
        )
    )

    # --------------------------------------------------------------
    # Corruption 4: unsupported factual assertion
    # --------------------------------------------------------------

    corrupted_draft["paragraphs"][0]["content"] += (
        " I personally inspected the redevelopment site "
        "on 1 August 2026."
    )

    return corrupted_draft


def test_phase4d_revision_loop():
    """
    Test the complete Phase 4D feedback cycle.

    Real valid draft
        ↓
    deliberate corruption
        ↓
    validation
        ↓
    evaluation
        ↓
    revision agent
        ↓
    validation
        ↓
    evaluation
    """

    (
        case_data,
        template_specification,
        content_map,
    ) = _build_phase4_inputs()

    # --------------------------------------------------------------
    # Generate a real valid draft first.
    #
    # We reuse the existing production generator indirectly by
    # importing the drafting node. This gives the test the exact
    # generated-draft structure used by the application.
    # --------------------------------------------------------------

    from src.agent.nodes import drafting_agent_node

    initial_state = {
        "case_data": case_data,
        "template_specification": template_specification,
        "content_map": content_map,
    }

    drafting_update = drafting_agent_node(
        initial_state
    )

    valid_draft = drafting_update["generated_draft"]

    assert valid_draft
    assert valid_draft["paragraphs"]

    # --------------------------------------------------------------
    # Deliberately corrupt the valid draft.
    # --------------------------------------------------------------

    corrupted_draft = _corrupt_draft(
        valid_draft
    )

    state = {
        "case_data": case_data,
        "template_specification": template_specification,
        "content_map": content_map,
        "generated_draft": corrupted_draft,
        "revision_count": 0,
        "evaluation_history": [],
    }

    # --------------------------------------------------------------
    # First validation.
    # --------------------------------------------------------------

    validation_update = validation_node(
        state
    )

    state.update(
        validation_update
    )

    initial_validation = state[
        "validation_results"
    ]

    # --------------------------------------------------------------
    # First evaluation.
    #
    # Use the same evaluator already proven in Phase 4C.1.
    # --------------------------------------------------------------

    initial_evaluation = evaluate_draft(
        state
    )

    state["evaluation_results"] = (
        initial_evaluation
    )

    print(
        "\n===== PHASE 4D INITIAL DEFECTIVE DRAFT ====="
    )

    print(
        "Validation passed:",
        initial_validation["passed"],
    )

    print(
        "Validation score:",
        initial_validation["score"],
    )

    print(
        "Evaluation score:",
        initial_evaluation["overall_score"],
    )

    print(
        "Initial issues:",
        len(initial_evaluation["issues"]),
    )

    assert initial_validation["passed"] is False

    assert initial_evaluation["issues"]

    # --------------------------------------------------------------
    # Revision Agent
    # --------------------------------------------------------------

    revision_update = revision_agent_node(
        state
    )

    state.update(
        revision_update
    )

    print(
        "\n===== PHASE 4D REVISION ====="
    )

    print(
        "Revision count:",
        state["revision_count"],
    )

    print(
        "Revision status:",
        state["status"],
    )

    assert state["revision_count"] == 1

    assert state["generated_draft"] != corrupted_draft

    assert len(
        state["evaluation_history"]
    ) == 1

    # --------------------------------------------------------------
    # Re-validation after revision.
    # --------------------------------------------------------------

    validation_update = validation_node(
        state
    )

    state.update(
        validation_update
    )

    revised_validation = state[
        "validation_results"
    ]

    # --------------------------------------------------------------
    # Re-evaluation after revision.
    # --------------------------------------------------------------

    evaluation_update = evaluation_agent_node(
        state
    )

    state.update(
        evaluation_update
    )

    revised_evaluation = state[
        "evaluation_results"
    ]

    print(
        "\n===== PHASE 4D REVISED RESULT ====="
    )

    print(
        "Validation passed:",
        revised_validation["passed"],
    )

    print(
        "Validation score:",
        revised_validation["score"],
    )

    print(
        "Evaluation score:",
        revised_evaluation["overall_score"],
    )

    print(
        "Remaining issues:",
        len(revised_evaluation["issues"]),
    )

    # --------------------------------------------------------------
    # The revision should have corrected the deliberately introduced
    # defects.
    # --------------------------------------------------------------

    assert revised_validation["passed"] is True

    assert revised_validation["error_count"] == 0

    assert not revised_evaluation["issues"]

    assert state["revision_count"] == 1

    assert state["status"] == "evaluation_completed"


def test_phase4d_revision_limit():
    """
    Verify that the Phase 4D router terminates after the maximum
    number of allowed revisions.
    """

    state = {
        "revision_count": MAX_REVISIONS,
        "evaluation_results": {
            "issues": [
                {
                    "dimension": "Hallucination Check",
                    "severity": "HIGH",
                    "issue": (
                        "Deliberately unresolved test issue."
                    ),
                }
            ]
        },
    }

    route = should_revise(
        state
    )

    print(
        "\n===== PHASE 4D REVISION LIMIT ====="
    )

    print(
        "Maximum revisions:",
        MAX_REVISIONS,
    )

    print(
        "Router decision:",
        route,
    )

    assert MAX_REVISIONS == 2

    assert route == "revision_limit_reached"