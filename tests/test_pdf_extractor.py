from pathlib import Path

from src.extraction.pdf_extractor import extract_pdf_text


PDF_FILES = [
    Path("data/reference/01 Affidavit Format Explained.pdf"),
    Path("data/reference/02 Affidavit in Reply Sample.docx.pdf"),
    Path("data/input/03_Case_Information.pdf"),
]


def test_all_supplied_pdfs_extract_successfully():
    for pdf_path in PDF_FILES:
        pages = extract_pdf_text(pdf_path)

        assert pages, f"No pages extracted from {pdf_path}"
        assert all(page.strip() for page in pages), (
            f"Empty page detected in {pdf_path}"
        )


def test_page_boundaries_are_preserved():
    expected_page_counts = {
        "01 Affidavit Format Explained.pdf": 3,
        "02 Affidavit in Reply Sample.docx.pdf": 2,
        "03_Case_Information.pdf": 2,
    }

    for pdf_path in PDF_FILES:
        pages = extract_pdf_text(pdf_path)

        assert len(pages) == expected_page_counts[pdf_path.name]