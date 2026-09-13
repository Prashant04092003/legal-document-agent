from __future__ import annotations

from src.extraction.pdf_extractor import extract_pdf_text
from src.template.reference_splitter import split_reference_sections
from src.template.schema import (
    ReplyMove,
    TemplateSection,
    TemplateSpecification,
)
from src.template.structure import REPLY_MOVES, TEMPLATE_SECTIONS
from src.template.template_knowledge import get_template_knowledge


def build_base_template_specification() -> TemplateSpecification:
    """
    Build the deterministic structural skeleton of the
    Affidavit in Reply from the supplied reference format.
    """

    sections = [
        TemplateSection(
            order=index,
            name=section_name,
            required=True,
        )
        for index, section_name in enumerate(TEMPLATE_SECTIONS, start=1)
    ]

    reply_moves = [
        ReplyMove(
            name=name,
            purpose=purpose,
            expected_position=position,
        )
        for name, purpose, position in REPLY_MOVES
    ]

    return TemplateSpecification(
        document_type="Affidavit in Reply",
        sections=sections,
        reply_moves=reply_moves,
    )


def analyze_template(reference_sections: dict) -> dict:
    """
    Build template knowledge deterministically from the
    authoritative reference document.

    No LLM is used here.

    The reference sections are accepted as an argument so the
    existing pipeline interface remains compatible.
    """

    required_sections = {
        "TEN_PARTS",
        "DEPONENT_RULE",
        "PARAGRAPH_SEQUENCE",
        "FIXED_PHRASES",
        "FORMATTING",
        "ENTITIES",
        "REPLY_MOVES",
        "FILL_IN_TEMPLATE",
        "NOT_COVERED",
    }

    missing_sections = required_sections - set(reference_sections)

    if missing_sections:
        raise ValueError(
            "Required reference sections are missing: "
            f"{sorted(missing_sections)}"
        )

    knowledge = get_template_knowledge()

    return {
        "document_type": knowledge["document_type"],
        "entities": knowledge["entities"],
        "fixed_phrases": knowledge["fixed_phrases"],
        "formatting_rules": knowledge["formatting_rules"],
        "consistency_rules": knowledge["consistency_rules"],
        "unsupported_elements": knowledge["unsupported_elements"],
        "deponent_rules": knowledge["deponent_rules"],
        "verification_verb_mapping": knowledge[
            "verification_verb_mapping"
        ],
        "paragraph_sequence": knowledge["paragraph_sequence"],
        "structural_rules": knowledge["structural_rules"],
    }


def analyze_reference_documents(
    format_explained_path: str,
    sample_affidavit_path: str,
) -> dict:
    """
    Extract the authoritative format reference and build
    deterministic template knowledge.

    The sample affidavit remains part of the public interface for
    compatibility with the existing pipeline, but the authoritative
    format rules come from the Format Explained document.
    """

    del sample_affidavit_path

    pages = extract_pdf_text(format_explained_path)
    reference_text = "\n\n".join(pages)

    reference_sections = split_reference_sections(reference_text)

    return analyze_template(reference_sections)


def build_template_specification(
    template_knowledge: dict,
) -> TemplateSpecification:
    """
    Combine deterministic structure, reply moves, entities and
    template rules into the TemplateSpecification contract.
    """

    specification = build_base_template_specification()

    specification.entities = list(
        template_knowledge["entities"]
    )

    specification.fixed_phrases = {
        key: list(value)
        for key, value in template_knowledge["fixed_phrases"].items()
    }

    specification.formatting_rules = dict(
        template_knowledge["formatting_rules"]
    )

    specification.consistency_rules = list(
        template_knowledge["consistency_rules"]
    )

    specification.unsupported_elements = list(
        template_knowledge["unsupported_elements"]
    )

    return specification