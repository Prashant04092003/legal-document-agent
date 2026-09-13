from pathlib import Path

from src.extraction.pdf_extractor import extract_pdf_text
from src.extraction.entity_extractor import extract_case_data
from src.mapping.content_mapper import build_content_map
from src.template.template_analyzer import build_base_template_specification


CASE_FILE = Path("data/input/03_Case_Information.pdf")


def test_build_content_map():
    # Phase 3A
    pages = extract_pdf_text(CASE_FILE)
    case_data = extract_case_data(pages)

    # Phase 2
    template_specification = build_base_template_specification()

    # Phase 3B
    content_map = build_content_map(
        case_data,
        template_specification,
    )

    # Basic contract
    assert content_map.document_type == "Affidavit in Reply"

    # Structural sections
    section_targets = [
        mapping.target
        for mapping in content_map.sections
    ]

    assert section_targets == [
        "FORUM_HEADING",
        "JURISDICTION",
        "CASE_NUMBER",
        "CAUSE_TITLE",
        "AFFIDAVIT_TITLE",
        "DEPONENT_CLAUSE",
    ]

    # Verify important mappings
    section_values = {
        mapping.target: mapping.value
        for mapping in content_map.sections
    }

    assert (
        section_values["FORUM_HEADING"]
        == "IN THE HIGH COURT OF JUDICATURE AT BOMBAY"
    )

    assert (
        section_values["JURISDICTION"]
        == "ORDINARY ORIGINAL CIVIL JURISDICTION"
    )

    assert (
        section_values["CASE_NUMBER"]
        == "WRIT PETITION No. 1847 of 2026"
    )

    assert (
        "Sunrise Housing Private Limited"
        in section_values["CAUSE_TITLE"]
    )

    assert (
        "Mumbai Metropolitan Region Development Authority"
        in section_values["CAUSE_TITLE"]
    )

    # Numbered paragraphs
    assert content_map.paragraph_count == 7
    assert len(content_map.paragraphs) == 7

    paragraph_numbers = [
        paragraph.paragraph_number
        for paragraph in content_map.paragraphs
    ]

    assert paragraph_numbers == [1, 2, 3, 4, 5, 6, 7]

    # First six paragraphs come from CaseData
    for index, paragraph in enumerate(
        content_map.paragraphs[:6],
        start=1,
    ):
        assert paragraph.source_type == "case_reply_point"
        assert (
            paragraph.source_reference
            == f"CaseData.reply_points[{index - 1}]"
        )
        assert paragraph.title == case_data.reply_points[index - 1].title
        assert (
            paragraph.content
            == case_data.reply_points[index - 1].content
        )

    # Closing paragraph comes from the template
    closing = content_map.paragraphs[6]

    assert closing.paragraph_number == 7
    assert closing.source_type == "template_move"
    assert closing.template_move == "CLOSING"
    assert closing.title == "Closing"

    # Exhibit
    assert content_map.exhibit is not None
    assert content_map.exhibit.target == "EXHIBIT"
    assert content_map.exhibit.value == "EXHIBIT-‘A’"

    # Prayer
    assert content_map.prayer is not None
    assert (
        content_map.prayer.value
        == case_data.prayer
    )

    # Jurat
    assert content_map.jurat is not None
    assert "solemnly affirm" in content_map.jurat.value
    assert "Arvind Rajan" in content_map.jurat.value
    assert "Mumbai" in content_map.jurat.value
    assert "5 September 2026" in content_map.jurat.value

    # Verification
    assert content_map.verification is not None
    assert (
        "paragraphs 1 to 7 and the Prayer"
        in content_map.verification.value
    )

    # Advocate
    assert content_map.advocate is not None
    assert "Rajan & Associates" in content_map.advocate.value
    assert "Respondent No. 2" in content_map.advocate.value