import json
import re

from src.llm.ollama_client import generate


ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


JSON_REPAIR_PROMPT = """
You are a JSON output repair utility.

The input was produced by another language model and may contain
terminal cursor corruption.

Your ONLY task is to reconstruct the intended JSON.

Rules:

1. Return exactly one JSON object.
2. Preserve every JSON key.
3. Preserve the original information.
4. Repair only obvious duplicated/truncated terminal fragments.
5. Do not summarize.
6. Do not shorten sentences.
7. Do not add information.
8. Do not invent legal content.
9. Preserve placeholders exactly.
10. Return ONLY JSON.
"""


def remove_ansi_sequences(text: str) -> str:
    """Remove ANSI terminal escape sequences."""

    return ANSI_ESCAPE_PATTERN.sub("", text)


def normalize_json_control_characters(text: str) -> str:
    """
    Make raw control characters safe inside JSON strings.

    Newlines and carriage returns inside JSON strings are converted
    to spaces because the extracted template phrases do not require
    meaningful line breaks.
    """

    result = []

    inside_string = False
    escaped = False

    for char in text:
        if escaped:
            result.append(char)
            escaped = False
            continue

        if char == "\\":
            result.append(char)
            escaped = True
            continue

        if char == '"':
            result.append(char)
            inside_string = not inside_string
            continue

        if inside_string and char in "\r\n\t":
            result.append(" ")
            continue

        result.append(char)

    return "".join(result)


def repair_json_output(raw_response: str) -> str:
    """
    Remove terminal artifacts and normalize obvious JSON control-character
    corruption. Only invoke the LLM repair step when deterministic cleanup
    is not sufficient.
    """

    cleaned_response = remove_ansi_sequences(raw_response)

    # First, return immediately if the response is already valid JSON.
    try:
        json.loads(cleaned_response)
        return cleaned_response
    except json.JSONDecodeError:
        pass

    # Try deterministic normalization before asking another LLM to repair it.
    normalized_response = normalize_json_control_characters(
        cleaned_response
    )

    try:
        json.loads(normalized_response)
        return normalized_response
    except json.JSONDecodeError:
        pass

    # Only use the LLM repair step when deterministic cleanup fails.
    prompt = f"""
{JSON_REPAIR_PROMPT}

INPUT:

{normalized_response}
""".strip()

    repaired_response = generate(prompt)

    repaired_response = remove_ansi_sequences(repaired_response)

    repaired_response = normalize_json_control_characters(
        repaired_response
    )

    # Confirm that the repair function returns valid JSON.
    json.loads(repaired_response)

    return repaired_response