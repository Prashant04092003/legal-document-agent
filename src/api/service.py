from pathlib import Path
from typing import Any

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


PROJECT_ROOT = Path(__file__).resolve().parents[2]

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

OUTPUT_DIR = PROJECT_ROOT / "outputs"


def run_affidavit_pipeline() -> dict[str, Any]:
    """
    Execute the existing legal-document generation and evaluation
    pipeline without changing the underlying Phase 1-7 implementation.

    Returns a serializable result containing:
    - evaluation report
    - generated document path
    - evaluation report path
    - workflow status
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
    # Phase 4-6 — Existing agent workflow
    # --------------------------------------------------------------

    result = run_drafting_agent(
        case_data,
        template_specification,
        content_map,
    )

    generated_draft = result.get("generated_draft")

    if not isinstance(generated_draft, dict):
        raise RuntimeError(
            "The drafting workflow did not produce a valid generated draft."
        )

    # --------------------------------------------------------------
    # Phase 7 — Evaluation report
    # --------------------------------------------------------------

    report = build_evaluation_report(result)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_output_path = (
        OUTPUT_DIR
        / "evaluation_report.json"
    )

    save_evaluation_report(
        report,
        report_output_path,
    )

    # --------------------------------------------------------------
    # Phase 8 — DOCX rendering
    # --------------------------------------------------------------

    affidavit_output_path = (
        OUTPUT_DIR
        / "affidavit_in_reply.docx"
    )

    render_affidavit_docx(
        generated_draft,
        affidavit_output_path,
    )

    return {
        "report": report,
        "status": result.get("status"),
        "revision_count": result.get(
            "revision_count",
            0,
        ),
        "evaluation_history_count": len(
            result.get("evaluation_history") or []
        ),
        "affidavit_path": str(
            affidavit_output_path
        ),
        "evaluation_report_path": str(
            report_output_path
        ),
    }