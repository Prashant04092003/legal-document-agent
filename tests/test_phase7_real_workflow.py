from pathlib import Path

from src.agent.graph import run_drafting_agent
from src.evaluation.report import (
    build_evaluation_report,
    save_evaluation_report,
)
from src.extraction.entity_extractor import extract_case_data
from src.extraction.pdf_extractor import extract_pdf_text
from src.mapping.content_mapper import build_content_map
from src.output.docx_renderer import render_affidavit_docx
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


def test_phase7_report_from_real_workflow():
    """
    Run the actual Phase 2-6 pipeline and verify that Phase 7
    can build and persist an evaluation report from the real
    final workflow state.

    Also render the actual Phase 4 generated draft into the
    assignment DOCX artifact.
    """

    # --------------------------------------------------------------
    # Phase 2 — Reference / template understanding
    # --------------------------------------------------------------

    template_knowledge = analyze_reference_documents(
        str(FORMAT_EXPLAINED),
        str(SAMPLE_AFFIDAVIT),
    )

    template_specification = build_template_specification(
        template_knowledge
    )

    # --------------------------------------------------------------
    # Phase 3 — Case extraction and content mapping
    # --------------------------------------------------------------

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

    # --------------------------------------------------------------
    # Phase 4-6 — Existing complete agent workflow
    # --------------------------------------------------------------

    result = run_drafting_agent(
        case_data,
        template_specification,
        content_map,
    )

    # --------------------------------------------------------------
    # Verify that the workflow actually produced a draft
    # --------------------------------------------------------------

    generated_draft = result.get("generated_draft")

    assert generated_draft is not None
    assert isinstance(generated_draft, dict)

    # --------------------------------------------------------------
    # Phase 7 — Build evaluation report
    # --------------------------------------------------------------

    report = build_evaluation_report(result)

    # --------------------------------------------------------------
    # Phase 7 — Persist evaluation report
    # --------------------------------------------------------------

    report_output_path = (
        PROJECT_ROOT
        / "outputs"
        / "evaluation_report.json"
    )

    saved_report_path = save_evaluation_report(
        report,
        report_output_path,
    )

    assert saved_report_path == report_output_path
    assert report_output_path.exists()

    # --------------------------------------------------------------
    # Phase 8 — Render actual generated draft
    # --------------------------------------------------------------

    affidavit_output_path = (
        PROJECT_ROOT
        / "outputs"
        / "affidavit_in_reply.docx"
    )

    saved_affidavit_path = render_affidavit_docx(
        generated_draft,
        affidavit_output_path,
    )

    assert saved_affidavit_path == affidavit_output_path
    assert affidavit_output_path.exists()
    assert affidavit_output_path.stat().st_size > 0

    # --------------------------------------------------------------
    # Basic report checks
    # --------------------------------------------------------------

    assert report["report_title"] == (
        "Affidavit in Reply - Evaluation Report"
    )

    assert report["document"]["document_type"] == (
        "Affidavit in Reply"
    )

    assert report["document"]["case_number"] == "1847"
    assert report["document"]["year"] == "2026"

    # --------------------------------------------------------------
    # The current real workflow is expected to pass.
    # --------------------------------------------------------------

    assert report["status"] == "PASS"

    assert report["overall_score"] == 100.0

    # --------------------------------------------------------------
    # All six required evaluation dimensions must be present.
    # --------------------------------------------------------------

    expected_dimensions = {
        "Entity Accuracy",
        "Completeness",
        "Structure",
        "Consistency",
        "Template Fidelity",
        "Hallucination Check",
    }

    assert set(
        report["dimension_scores"].keys()
    ) == expected_dimensions

    assert all(
        0 <= score <= 100
        for score in report["dimension_scores"].values()
    )

    # --------------------------------------------------------------
    # Current real run should have no detected issues.
    # --------------------------------------------------------------

    assert report["issues"] == []

    # --------------------------------------------------------------
    # Deterministic validation results must be represented.
    # --------------------------------------------------------------

    deterministic = (
        report["validation_summary"]["deterministic"]
    )

    assert deterministic["passed"] is True
    assert deterministic["score"] == 100.0
    assert deterministic["error_count"] == 0
    assert deterministic["errors"] == []

    # --------------------------------------------------------------
    # Semantic evaluation results must be represented.
    # --------------------------------------------------------------

    semantic = report["validation_summary"]["semantic"]

    assert semantic["passed"] is True
    assert semantic["issue_count"] == 0
    assert semantic["summary"]

    # --------------------------------------------------------------
    # Scoring information must be preserved.
    # --------------------------------------------------------------

    assert report["scoring"]["weights"] == {
        "Entity Accuracy": 0.20,
        "Completeness": 0.20,
        "Structure": 0.15,
        "Consistency": 0.15,
        "Template Fidelity": 0.15,
        "Hallucination Check": 0.15,
    }

    assert "weighted average" in report["scoring"]["method"]

    # --------------------------------------------------------------
    # Revision information
    # --------------------------------------------------------------

    assert report["revision"]["revision_count"] == (
        result.get("revision_count", 0)
    )

    assert report["revision"]["evaluation_history_count"] == (
        len(result.get("evaluation_history") or [])
    )

    # --------------------------------------------------------------
    # Model information
    # --------------------------------------------------------------

    assert report["model"] == "qwen2.5:7b"

    # --------------------------------------------------------------
    # Final artifact checks
    # --------------------------------------------------------------

    assert report_output_path.name == "evaluation_report.json"
    assert affidavit_output_path.name == "affidavit_in_reply.docx"