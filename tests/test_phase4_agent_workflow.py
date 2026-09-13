from copy import deepcopy
from pathlib import Path

from src.agent.graph import run_drafting_agent
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
    """Build the real Phase 2/3 inputs used by the agent."""

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


def test_phase4_drafting_and_validation_workflow():
    (
        case_data,
        template_specification,
        content_map,
    ) = _build_phase4_inputs()

    # ==============================================================
    # PHASE 4B + 4C — normal production workflow
    # ==============================================================

    result = run_drafting_agent(
        case_data,
        template_specification,
        content_map,
    )

    validation = result["validation_results"]

    print("\n===== PHASE 4B RESULT =====")
    print("Status:", result["status"])
    print("Validation passed:", validation["passed"])
    print("Validation score:", validation["score"])
    print("Errors:", validation["error_count"])

    print("\n===== DETERMINISTIC DIMENSION SCORES =====")

    for dimension, score in validation[
        "dimension_scores"
    ].items():
        print(f"{dimension}: {score}")

    if validation["errors"]:
        print("\n===== VALIDATION ERRORS =====")

        for error in validation["errors"]:
            print(error)

    assert validation["passed"] is True
    assert validation["error_count"] == 0
    assert validation["score"] == 100.0

    # ==============================================================
    # PHASE 4C — normal hybrid evaluation
    # ==============================================================

    evaluation = result["evaluation_results"]

    print("\n===== PHASE 4C RESULT =====")
    print(
        "Overall Evaluation Score:",
        evaluation["overall_score"],
    )

    print("\n===== HYBRID DIMENSION SCORES =====")

    for dimension, score in evaluation[
        "dimension_scores"
    ].items():
        print(f"{dimension}: {score}")

    print("\n===== DETERMINISTIC EVALUATION ISSUES =====")

    for issue in evaluation[
        "deterministic_issues"
    ]:
        print(issue)

    print("\n===== SEMANTIC EVALUATION ISSUES =====")

    for issue in evaluation[
        "semantic_issues"
    ]:
        print(issue)

    print("\n===== HYBRID SUMMARY =====")
    print(evaluation["summary"])

    expected_dimensions = {
        "Entity Accuracy",
        "Completeness",
        "Structure",
        "Consistency",
        "Template Fidelity",
        "Hallucination Check",
    }

    assert set(
        evaluation["dimension_scores"].keys()
    ) == expected_dimensions

    assert all(
        0 <= score <= 100
        for score in evaluation[
            "dimension_scores"
        ].values()
    )

    assert 0 <= evaluation["overall_score"] <= 100

    assert isinstance(
        evaluation["issues"],
        list,
    )

    assert isinstance(
        evaluation["deterministic_issues"],
        list,
    )

    assert isinstance(
        evaluation["semantic_issues"],
        list,
    )

    assert evaluation["summary"].strip()

    assert evaluation["model"] == "qwen2.5:7b"

    # ==============================================================
    # PHASE 4C.1 — adversarial hybrid evaluator test
    # ==============================================================

    corrupted_draft = deepcopy(
        result["generated_draft"]
    )

    # --------------------------------------------------------------
    # Corruption 1: wrong case number
    #
    # Source:
    #   WRIT PETITION No. 1847 of 2026
    #
    # Corrupted:
    #   WRIT PETITION No. 9999 of 2026
    # --------------------------------------------------------------

    corrupted_draft["sections"]["CASE_NUMBER"] = (
        "WRIT PETITION No. 9999 of 2026"
    )

    # --------------------------------------------------------------
    # Corruption 2: remove a material source point
    #
    # Paragraph 4 corresponds to the first substantive
    # reply point. Replace it with generic language.
    # --------------------------------------------------------------

    if len(corrupted_draft["paragraphs"]) >= 4:
        corrupted_draft["paragraphs"][3]["content"] = (
            "With reference to the Petition, I deny the allegations."
        )

    # --------------------------------------------------------------
    # Corruption 3: wrong verification paragraph range
    #
    # Correct:
    #   paragraphs 1 to 7
    #
    # Corrupted:
    #   paragraphs 1 to 5
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

    corrupted_state = {
        "case_data": case_data,
        "template_specification": template_specification,
        "content_map": content_map,
        "generated_draft": corrupted_draft,
        "validation_results": {},
    }

    adversarial_evaluation = evaluate_draft(
        corrupted_state
    )

    print("\n===== PHASE 4C.1 ADVERSARIAL RESULT =====")

    print(
        "Overall Evaluation Score:",
        adversarial_evaluation["overall_score"],
    )

    print("\n===== ADVERSARIAL DIMENSION SCORES =====")

    for dimension, score in adversarial_evaluation[
        "dimension_scores"
    ].items():
        print(f"{dimension}: {score}")

    print(
        "\n===== ADVERSARIAL DETERMINISTIC ISSUES ====="
    )

    for issue in adversarial_evaluation[
        "deterministic_issues"
    ]:
        print(issue)

    print(
        "\n===== ADVERSARIAL SEMANTIC ISSUES ====="
    )

    for issue in adversarial_evaluation[
        "semantic_issues"
    ]:
        print(issue)

    print(
        "\n===== ADVERSARIAL SUMMARY ====="
    )

    print(
        adversarial_evaluation["summary"]
    )

    # ==============================================================
    # ADVERSARIAL ASSERTIONS
    #
    # These assertions prove that the evaluator is capable of
    # detecting deliberately introduced errors.
    # ==============================================================

    assert (
        adversarial_evaluation["overall_score"]
        < 100
    )

    assert len(
        adversarial_evaluation["issues"]
    ) > 0

    # --------------------------------------------------------------
    # Deterministic evidence must detect the wrong case number.
    # --------------------------------------------------------------

    deterministic_issue_text = " ".join(
        (
            issue["issue"]
            + " "
            + str(issue.get("expected", ""))
            + " "
            + str(issue.get("actual", ""))
        )
        for issue in adversarial_evaluation[
            "deterministic_issues"
        ]
    ).lower()

    assert (
        "case number" in deterministic_issue_text
        or "9999" in deterministic_issue_text
        or "1847" in deterministic_issue_text
    )

    # --------------------------------------------------------------
    # Deterministic evidence must detect the incorrect
    # verification paragraph range.
    # --------------------------------------------------------------

    assert (
        "verification" in deterministic_issue_text
        or "paragraph" in deterministic_issue_text
    )

    # --------------------------------------------------------------
    # Semantic evaluation must produce at least one finding.
    #
    # The deliberately weakened substantive paragraph and/or
    # unsupported site-inspection statement should give the
    # semantic evaluator something to flag.
    # --------------------------------------------------------------

    semantic_issue_text = " ".join(
        (
            issue["issue"]
            + " "
            + issue["evidence"]
        )
        for issue in adversarial_evaluation[
            "semantic_issues"
        ]
    ).lower()

    assert len(
        adversarial_evaluation["semantic_issues"]
    ) > 0

    assert (
        "inspect" in semantic_issue_text
        or "august" in semantic_issue_text
        or "unsupported" in semantic_issue_text
        or "halluc" in semantic_issue_text
        or "source" in semantic_issue_text
        or "paragraph" in semantic_issue_text
        or "content" in semantic_issue_text
    )