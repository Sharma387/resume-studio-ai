import re


def extract_json(text: str) -> str:
    """Extract a JSON object or array from AI response, stripping markdown.

    Arrays have to be handled explicitly. Slicing from the first ``{`` to the
    last ``}`` silently rewrites a bare ``[{...}, {...}]`` into ``{...}, {...}``,
    which is invalid JSON and loses the whole section, or — with a single item —
    quietly collapses several roles into one. Models asked for a wrapped object
    routinely answer with a bare array, so this shape is normal, not an error.
    """
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    inner = match.group(1).strip() if match else text.strip()

    if inner.lstrip().startswith("["):
        start, end = inner.find("["), inner.rfind("]")
        if start != -1 and end > start:
            return inner[start : end + 1]
        return inner

    brace_start = inner.find("{")
    brace_end = inner.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        return inner[brace_start : brace_end + 1]
    return inner


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
