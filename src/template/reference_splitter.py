from __future__ import annotations

from typing import Dict


SECTION_MARKERS = {
    "TEN_PARTS": "1. The ten parts",
    "DEPONENT_RULE": "2. Deponent rule (Part 6)",
    "PARAGRAPH_SEQUENCE": "3. Paragraph sequence (Part 7)",
    "FIXED_PHRASES": "4. Fixed phrases",
    "FORMATTING": "5. Formatting",
    "ENTITIES": "6. Entities to extract",
    "REPLY_MOVES": "7. Reply moves",
    "FILL_IN_TEMPLATE": "8. Fill-in template",
    "NOT_COVERED": "9. Not covered here",
}


def split_reference_sections(reference_text: str) -> Dict[str, str]:
    """
    Split the Affidavit Format Explained text into logical sections.

    The splitter is deterministic and does not use an LLM.
    """

    positions = []

    for name, marker in SECTION_MARKERS.items():
        position = reference_text.find(marker)

        if position == -1:
            raise ValueError(
                f"Required reference section not found: {marker}"
            )

        positions.append((position, name, marker))

    positions.sort()

    sections = {}

    for index, (start, name, marker) in enumerate(positions):
        if index + 1 < len(positions):
            end = positions[index + 1][0]
        else:
            end = len(reference_text)

        section_text = reference_text[start:end].strip()

        sections[name] = section_text

    return sections