"""
Deterministic template knowledge for the Affidavit in Reply.

Source of truth:
    01 Affidavit Format Explained.pdf

This module intentionally contains no LLM calls.

The reference document defines a fixed format for the proof-of-concept
Affidavit in Reply. Since that reference is static and authoritative,
its rules are encoded directly rather than inferred by an LLM at
runtime.
"""

from __future__ import annotations


DOCUMENT_TYPE = "Affidavit in Reply"


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

ENTITIES = [
    "FORUM / CITY",
    "JURISDICTION_TYPE",
    "CASE_TYPE / CASE_NUMBER / YEAR",
    "PETITIONER",
    "RESPONDENT",
    "RESPONDENT_NUMBER",
    "DEPONENT",
    "CAPACITY",
    "ORGANISATION",
    "ADDRESS / AGE / OCCUPATION",
    "VERIFICATION_VERB",
    "PLACE_OF_ATTESTATION / DATE",
    "PARAGRAPH_COUNT",
]


# ---------------------------------------------------------------------------
# Fixed phrases
# ---------------------------------------------------------------------------

FIXED_PHRASES = {
    "DEPONENT_CLAUSE": [
        "the Respondent No.__ above named",
        "do hereby solemnly affirm and state as under:",
    ],
    "PARAGRAPH_1": [
        "am well acquainted with the facts and circumstances of the case",
        "I have perused the Petition and the documents annexed thereto",
        "am competent to affirm this Affidavit in Reply",
    ],
    "BLANKET_DENIAL": [
        "At the outset, I deny each and every allegation, contention and submission",
        "save and except those specifically admitted herein",
        "misconceived, devoid of merits and is liable to be dismissed in limine",
    ],
    "PRELIMINARY_POSITION": [
        "has suppressed material facts",
        "strictly in accordance with law and after following due procedure",
        "No legal, constitutional or fundamental right... has been infringed",
    ],
    "SUBSTANTIVE_ANSWER": [
        "With reference to the averments made in the Petition",
        "the same are false, incorrect and denied",
        "has failed to make out any case warranting interference",
        "the extraordinary writ jurisdiction of this Hon'ble Court",
    ],
    "CLOSING": [
        "In the premises aforesaid",
        "deserves to be dismissed with costs",
    ],
    "PRAYER": [
        "I therefore respectfully pray that this Hon'ble Court may be pleased to:",
        "grant such other and further reliefs as this Hon'ble Court may deem fit and proper",
    ],
    "VERIFICATION": [
        "true and correct to my knowledge and belief",
        "nothing material has been concealed therefrom",
    ],
    "DATE_FORMAT": [
        "ordinal day + month + year",
        "5th day of September 2026",
    ],
}


# ---------------------------------------------------------------------------
# Formatting rules
# ---------------------------------------------------------------------------

FORMATTING_RULES = {
    "forum_heading": "Bold, ALL CAPS, centred.",
    "jurisdiction": "Bold, ALL CAPS, centred.",
    "case_number": "Bold, ALL CAPS, centred. NO. and OF are fixed words.",
    "affidavit_title": "Bold, ALL CAPS, centred.",
    "prayer_heading": "Bold, ALL CAPS, centred.",
    "verification_heading": "Bold, ALL CAPS, centred.",
    "cause_title_party_names": "Normal, left.",
    "cause_title_status_tags": "Right-aligned. Tags begin with three dots.",
    "versus": "Centred, own line.",
    "paragraph_numbers": "Bold.",
    "prayer_letters": "Bold.",
    "paragraph_text": "Normal, justified.",
    "deponent": "ALL CAPS, right-aligned.",
    "before_me": "Normal, left-aligned.",
    "jurat": "Solemnly affirmed at [PLACE] / On this [Nth] day of [Month] [Year].",
    "verification_place_date": "Place and date repeat the jurat.",
}


# ---------------------------------------------------------------------------
# Consistency rules
# ---------------------------------------------------------------------------

CONSISTENCY_RULES = [
    "Verification verb in Part 6 must match the jurat verb in Part 9.",
    "Paragraph range in Part 10 must match the actual number of body paragraphs.",
    "Respondent numbering must remain consistent throughout the affidavit.",
]


# ---------------------------------------------------------------------------
# Unsupported elements
# ---------------------------------------------------------------------------

UNSUPPORTED_ELEMENTS = [
    "exhibit references",
    "advocate / drafting block",
    "para-wise reply",
    "tribunal and board formats (BEFORE THE...)",
    "statutory citations",
    "case-law citations",
    "monetary amounts",
]


# ---------------------------------------------------------------------------
# Deponent rules
# ---------------------------------------------------------------------------

DEPONENT_RULES = {
    "person_respondent": (
        "Respondent is a person → that person deposes: "
        '"the Respondent No.2 above named".'
    ),
    "organisation_respondent": (
        "Respondent is a company or authority → an officer deposes for it: "
        '"the [designation] of the Respondent No.2 above named".'
    ),
    "organisation_restriction": (
        'Never write "I am the Respondent No.2" for an organisation.'
    ),
}


# ---------------------------------------------------------------------------
# Verification / jurat verb mapping
# ---------------------------------------------------------------------------

VERIFICATION_VERB_MAPPING = {
    "solemnly affirm": "Solemnly affirmed",
    "swear and affirm": "Sworn",
}


# ---------------------------------------------------------------------------
# Paragraph sequence
# ---------------------------------------------------------------------------

PARAGRAPH_SEQUENCE = [
    {
        "position": "1",
        "move": "IDENTITY_AND_PERUSAL",
        "opening_words": (
            "I say that I am the Respondent No.__ in the above Writ Petition "
            "and am well acquainted with the facts and circumstances of the case..."
        ),
    },
    {
        "position": "2",
        "move": "BLANKET_DENIAL",
        "opening_words": (
            "At the outset, I deny each and every allegation, contention and "
            "submission made in the Writ Petition, save and except those "
            "specifically admitted herein..."
        ),
    },
    {
        "position": "3",
        "move": "PRELIMINARY_POSITION",
        "opening_words": (
            "I say that the Petitioner has suppressed material facts... "
            "The action complained of has been taken strictly in accordance "
            "with law..."
        ),
    },
    {
        "position": "4 onward",
        "move": "SUBSTANTIVE_ANSWER",
        "opening_words": (
            "With reference to the averments made in the Petition, I say "
            "that the same are false, incorrect and denied..."
        ),
    },
    {
        "position": "Last",
        "move": "CLOSING",
        "opening_words": (
            "In the premises aforesaid, I say that the Writ Petition "
            "deserves to be dismissed with costs."
        ),
    },
]


# ---------------------------------------------------------------------------
# Template-level structural rules
# ---------------------------------------------------------------------------

STRUCTURAL_RULES = {
    "section_count": 10,
    "all_sections_required": True,
    "continuous_body_paragraph_sequence": True,
    "prayer_is_part_of_body_sequence": False,
    "prayer_uses_letters": True,
    "body_uses_numbers": True,
    "case_number_fixed_words": ["NO.", "OF"],
    "jurisdiction_must_end_with": "JURISDICTION",
    "affidavit_title_must_carry_respondent_number": True,
    "cause_title_versus_on_own_line": True,
}


def get_template_knowledge() -> dict:
    """
    Return the complete deterministic template knowledge contract.

    The returned structure matches the fields expected by
    build_template_specification() in template_analyzer.py.
    """

    return {
        "document_type": DOCUMENT_TYPE,
        "entities": list(ENTITIES),
        "fixed_phrases": {
            key: list(value)
            for key, value in FIXED_PHRASES.items()
        },
        "formatting_rules": dict(FORMATTING_RULES),
        "consistency_rules": list(CONSISTENCY_RULES),
        "unsupported_elements": list(UNSUPPORTED_ELEMENTS),
        "deponent_rules": dict(DEPONENT_RULES),
        "verification_verb_mapping": dict(VERIFICATION_VERB_MAPPING),
        "paragraph_sequence": [
            dict(item)
            for item in PARAGRAPH_SEQUENCE
        ],
        "structural_rules": dict(STRUCTURAL_RULES),
    }