from pathlib import Path

from src.agent.graph import run_drafting_agent
from src.extraction.entity_extractor import extract_case_data
from src.extraction.pdf_extractor import extract_pdf_text
from src.mapping.content_mapper import map_content
from src.template.template_analyzer import build_template_specification


def test_affidavit_drafting_graph():
    case_path = Path(
        "data/input/03_Case_Information.pdf"
    )

    pages = extract_pdf_text(case_path)

    case_data = extract_case_data(pages)

    template_specification = (
        build_template_specification(
            {
                "fixed_phrases": {},
                "formatting_rules": {},
                "consistency_rules": [],
                "unsupported_elements": [],
            }
        )
    )

    content_map = map_content(
        case_data,
        template_specification,
    )

    result = run_drafting_agent(
        case_data,
        template_specification,
        content_map,
    )

    draft = result["generated_draft"]

    assert result["status"] == "draft_generated"
    assert draft["document_type"] == "Affidavit in Reply"
    assert len(draft["paragraphs"]) == content_map.paragraph_count
    assert [
        paragraph["paragraph_number"]
        for paragraph in draft["paragraphs"]
    ] == list(range(1, content_map.paragraph_count + 1))