from pathlib import Path

from src.extraction.pdf_extractor import extract_pdf_text


def build_template_input(
    format_explained_path: str | Path,
    sample_affidavit_path: str | Path,
) -> str:
    """
    Extract and combine the two reference documents into a single
    structured input for the template-understanding stage.
    """

    format_pages = extract_pdf_text(format_explained_path)
    sample_pages = extract_pdf_text(sample_affidavit_path)

    format_text = "\n\n".join(
        f"--- Page {i} ---\n{page}"
        for i, page in enumerate(format_pages, start=1)
    )

    sample_text = "\n\n".join(
        f"--- Page {i} ---\n{page}"
        for i, page in enumerate(sample_pages, start=1)
    )

    return f"""
REFERENCE MATERIAL 1: AFFIDAVIT FORMAT EXPLAINED

{format_text}

============================================================

REFERENCE MATERIAL 2: AFFIDAVIT IN REPLY SAMPLE

{sample_text}
""".strip()