from src.llm.ollama_client import generate
from src.template.response_parser import parse_json_response

FIXED_PHRASES_PROMPT = """
You are extracting reusable wording from a legal document template.

TARGET DOCUMENT:
Affidavit in Reply

Use ONLY the supplied reference material.

Your task is ONLY to identify recurring phrases that can be reused
when generating another Affidavit in Reply.

Do NOT:
- generate an affidavit
- reproduce the complete sample
- return a fill-in template
- extract case-specific names
- extract case numbers
- extract dates
- extract addresses
- extract sample-specific facts
- perform legal research

Return ONLY valid JSON.

The JSON MUST contain exactly one key:

{
  "fixed_phrases": {}
}

Use these keys where supported by the reference:

- DEPONENT_CLAUSE
- IDENTITY_AND_PERUSAL
- BLANKET_DENIAL
- PRELIMINARY_POSITION
- SUBSTANTIVE_ANSWER
- CLOSING
- PRAYER
- JURAT
- VERIFICATION

Values must contain reusable template wording, using placeholders
such as [NAME], [N], [PROCEEDING TYPE], [PLACE], or [DATE] where
appropriate.

Do not include the actual sample case's names, case number,
dates, or other case-specific values.

Return no explanation and no Markdown.
"""


def extract_fixed_phrases(reference_text: str) -> dict:
    """
    Ask the LLM to extract only reusable template phrases.
    """

    prompt = f"""
{FIXED_PHRASES_PROMPT}

REFERENCE MATERIAL:

{reference_text}
""".strip()

    return generate(prompt)

FORMATTING_RULES_PROMPT = """
You are extracting formatting rules from a legal document template.

TARGET DOCUMENT:
Affidavit in Reply

Use ONLY the supplied reference material.

Your task is ONLY to identify explicitly stated formatting rules.

Do NOT:
- generate an affidavit
- reproduce the sample
- create a fill-in template
- extract case-specific information
- perform legal research
- infer formatting rules that are not stated

Focus only on:

- bold text
- ALL CAPS
- centered headings
- left/right alignment
- paragraph numbering
- prayer lettering
- paragraph justification
- DEPONENT placement
- Before Me placement
- VERSUS placement
- cause-title alignment

Return ONLY valid JSON.

The JSON MUST contain exactly one key:

{
  "formatting_rules": {}
}

Use concise rule descriptions as values.

Return no explanation and no Markdown.
"""


def extract_formatting_rules(reference_text: str) -> str:
    """
    Ask the LLM to extract only reusable formatting rules.
    """

    prompt = f"""
{FORMATTING_RULES_PROMPT}

REFERENCE MATERIAL:

{reference_text}
""".strip()

    return generate(prompt)

CONSISTENCY_RULES_PROMPT = """
You are extracting consistency rules from a legal document template.

TARGET DOCUMENT:
Affidavit in Reply

Use ONLY the supplied reference material.

Your task is ONLY to identify explicitly stated rules that ensure
different parts of the affidavit remain internally consistent.

Focus especially on:

- the verification verb matching the jurat verb
- the verification paragraph range matching the actual number
  of numbered body paragraphs
- respondent numbering consistency

Do NOT:
- generate an affidavit
- reproduce the sample
- create a fill-in template
- extract case-specific facts
- perform legal research
- invent additional legal rules

Return ONLY valid JSON.

The JSON MUST contain exactly one key:

{
  "consistency_rules": []
}

Each item in the array must be a concise description of one
consistency rule explicitly supported by the reference.

Return no explanation and no Markdown.
"""


def extract_consistency_rules(reference_text: str) -> str:
    """
    Ask the LLM to extract only template consistency rules.
    """

    prompt = f"""
{CONSISTENCY_RULES_PROMPT}

REFERENCE MATERIAL:

{reference_text}
""".strip()

    return generate(prompt)

UNSUPPORTED_ELEMENTS_PROMPT = """
You are extracting scope limitations from a legal document template.

TARGET DOCUMENT:
Affidavit in Reply

Use ONLY the supplied reference material.

Your task is ONLY to identify elements that the reference explicitly
states are NOT covered or prescribed by the template.

The reference may mention examples such as:

- exhibit references
- advocate / drafting block
- para-wise reply
- tribunal / board formats
- statutory citations
- case-law citations
- monetary amounts

Only include an element if the reference explicitly identifies it
as not covered, not prescribed, or outside the defined format.

Do NOT:
- generate an affidavit
- reproduce the sample
- create a fill-in template
- extract case-specific information
- perform legal research
- add limitations based on general legal knowledge

Return ONLY valid JSON.

The JSON MUST contain exactly one key:

{
  "unsupported_elements": []
}

Each item must be a concise description of one explicitly
unsupported element.

Return no explanation and no Markdown.
"""


def extract_unsupported_elements(reference_text: str) -> str:
    """
    Ask the LLM to extract only explicitly unsupported elements.
    """

    prompt = f"""
{UNSUPPORTED_ELEMENTS_PROMPT}

REFERENCE MATERIAL:

{reference_text}
""".strip()

    return generate(prompt)

def extract_template_knowledge(reference_text: str) -> dict:
    """
    Run the focused LLM extraction tasks independently and
    combine their validated JSON responses.
    """

    fixed_phrases = parse_json_response(
        extract_fixed_phrases(reference_text)
    )

    formatting_rules = parse_json_response(
        extract_formatting_rules(reference_text)
    )

    consistency_rules = parse_json_response(
        extract_consistency_rules(reference_text)
    )

    unsupported_elements = parse_json_response(
        extract_unsupported_elements(reference_text)
    )

    return {
        "fixed_phrases": fixed_phrases["fixed_phrases"],
        "formatting_rules": formatting_rules["formatting_rules"],
        "consistency_rules": consistency_rules["consistency_rules"],
        "unsupported_elements": unsupported_elements["unsupported_elements"],
    }