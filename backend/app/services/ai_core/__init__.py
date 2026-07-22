"""Shared AI infrastructure for resume processing services."""

import json
import logging
import re

from app.core.config import settings
from app.services.omniroute_service import OmniRouteService, OmniRouteError

logger = logging.getLogger(__name__)


def extract_json(text: str) -> str:
    """Extract JSON from AI response, stripping markdown code blocks if present."""
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        return text[brace_start : brace_end + 1]
    brace_start = text.find("[")
    brace_end = text.rfind("]")
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
