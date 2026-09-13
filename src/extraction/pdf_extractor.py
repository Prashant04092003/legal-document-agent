from pathlib import Path

import pymupdf


def extract_pdf_text(pdf_path: str | Path) -> list[str]:
    """
    Extract text from a PDF while preserving page boundaries.

    Returns:
        A list where each item contains the text extracted from one page.
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pages = []

    with pymupdf.open(pdf_path) as document:
        for page in document:
            pages.append(page.get_text("text"))

    return pages