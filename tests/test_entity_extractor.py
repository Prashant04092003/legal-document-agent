from pathlib import Path

from src.extraction.pdf_extractor import extract_pdf_text
from src.extraction.entity_extractor import extract_case_data


CASE_FILE = Path("data/input/03_Case_Information.pdf")


def test_extract_case_data():
    pages = extract_pdf_text(CASE_FILE)
    case_data = extract_case_data(pages)

    # Court and case details
    assert case_data.document_type == "Affidavit in Reply"
    assert case_data.court == "IN THE HIGH COURT OF JUDICATURE AT BOMBAY"
    assert case_data.jurisdiction == "ORDINARY ORIGINAL CIVIL JURISDICTION"
    assert case_data.proceeding_type == "WRIT PETITION"
    assert case_data.case_number == "1847"
    assert case_data.year == "2026"
    assert case_data.petitioner == "Sunrise Housing Private Limited"

    # Respondents
    assert case_data.respondents["1"] == "State of Maharashtra"
    assert (
        case_data.respondents["2"]
        == "Mumbai Metropolitan Region Development Authority"
    )

    assert case_data.filed_on_behalf_of == "Respondent No. 2"

    # Deponent
    assert case_data.deponent_name == "Arvind Rajan"
    assert case_data.designation == "Deputy Metropolitan Commissioner"
    assert (
        case_data.organisation
        == "Mumbai Metropolitan Region Development Authority"
    )
    assert case_data.address == "Bandra East, Mumbai, Maharashtra"
    assert case_data.verification_verb == "solemnly affirm"

    # Reply points
    assert len(case_data.reply_points) == 6

    assert case_data.reply_points[0].number == 1
    assert case_data.reply_points[0].title == "Filing of Affidavit in Reply"
    assert len(case_data.reply_points[0].content) == 2

    assert case_data.reply_points[1].number == 2
    assert case_data.reply_points[1].title == "General Denial"
    assert len(case_data.reply_points[1].content) == 2

    assert case_data.reply_points[2].number == 3
    assert case_data.reply_points[2].title == "Preliminary Position"
    assert len(case_data.reply_points[2].content) == 2

    assert case_data.reply_points[3].number == 4
    assert (
        case_data.reply_points[3].title
        == "Denial Regarding the Communication"
    )
    assert len(case_data.reply_points[3].content) == 1

    assert case_data.reply_points[4].number == 5
    assert (
        case_data.reply_points[4].title
        == "Authority for the Communication"
    )
    assert len(case_data.reply_points[4].content) == 1

    assert case_data.reply_points[5].number == 6
    assert case_data.reply_points[5].title == "Document Relied Upon"
    assert len(case_data.reply_points[5].content) == 2

    # Important content preservation checks
    assert "Sunrise Housing Private Limited" in (
        case_data.reply_points[0].content[0]
    )

    assert "15 July 2026" in (
        case_data.reply_points[3].content[0]
    )

    # Prayer
    assert (
        case_data.prayer
        == "Respondent No. 2 prays that the Writ Petition be dismissed with costs."
    )

    # Exhibit
    assert case_data.exhibit == "EXHIBIT-‘A’"

    # Attestation
    assert case_data.attestation_place == "Mumbai"
    assert case_data.attestation_date == "5 September 2026"

    # Advocate
    assert case_data.advocate_firm == "Rajan & Associates"
    assert case_data.advocate_for == "Respondent No. 2"