import re


def extract_json(text: str) -> str:
    """Extract a JSON object from AI response, stripping markdown code blocks."""
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        return text[brace_start : brace_end + 1]
    return text.strip()


def extract_json_array(text: str) -> str:
    """Extract a JSON array from AI response, stripping markdown."""
    match = re.search(r"```(?:json)?\s*\n?(\[.*?\])\n?```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    brace_start = text.find("[")
    brace_end = text.rfind("]")
    if brace_start != -1 and brace_end > brace_start:
        return text[brace_start : brace_end + 1]
    return text.strip()
