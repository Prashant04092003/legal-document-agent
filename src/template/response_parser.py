import json


REQUIRED_TEMPLATE_KNOWLEDGE_KEYS = {
    "fixed_phrases",
    "formatting_rules",
    "consistency_rules",
    "unsupported_elements",
}


def parse_json_response(raw_response: str) -> dict:
    """
    Parse a JSON response returned by the LLM.

    Markdown code fences are removed if present.
    """

    cleaned = raw_response.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()

        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        cleaned = "\n".join(lines).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError("LLM response is not valid JSON") from exc

    if not isinstance(data, dict):
        raise ValueError("LLM response must be a JSON object")

    return data


def parse_template_knowledge(raw_response: str) -> dict:
    """
    Parse and validate the original combined template-knowledge
    response contract.
    """

    data = parse_json_response(raw_response)

    actual_keys = set(data.keys())

    if actual_keys != REQUIRED_TEMPLATE_KNOWLEDGE_KEYS:
        missing = REQUIRED_TEMPLATE_KNOWLEDGE_KEYS - actual_keys
        extra = actual_keys - REQUIRED_TEMPLATE_KNOWLEDGE_KEYS

        raise ValueError(
            f"Invalid template knowledge keys. "
            f"Missing: {sorted(missing)}; "
            f"Extra: {sorted(extra)}"
        )

    if not isinstance(data["fixed_phrases"], dict):
        raise ValueError("fixed_phrases must be an object")

    if not isinstance(data["formatting_rules"], dict):
        raise ValueError("formatting_rules must be an object")

    if not isinstance(data["consistency_rules"], list):
        raise ValueError("consistency_rules must be an array")

    if not isinstance(data["unsupported_elements"], list):
        raise ValueError("unsupported_elements must be an array")

    return data