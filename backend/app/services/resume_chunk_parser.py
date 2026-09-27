"""AI parsing of resume chunks, with results merged into a Resume.

Each chunk is parsed by the model on its own — the prompt names the section
so the model only emits fields that belong there, which keeps every
response small enough to generate quickly on a local model. A final
verification pass asks the model to check the merged resume against the
original text and report any fact that is missing, so omissions surface
instead of passing silently.
"""

from __future__ import annotations

import json
import logging
import re

from app.services.ai_core import extract_json
from app.services.resume_chunker import chunk_resume

logger = logging.getLogger(__name__)

CHUNK_PROMPTS: dict[str, str] = {
    "header": (
        "Extract the candidate's contact header. Return ONLY JSON: "
        '{"full_name", "professional_title", "phone", "email", "location", '
        '"linkedin", "github", "website"}. Use null for anything absent. '
        "linkedin/github/website must be full URLs."
    ),
    "summary": (
        "Extract the professional summary/profile text VERBATIM. "
        'Return ONLY JSON: {"summary": "<the full paragraph>"}.'
    ),
    "skills": (
        "Extract the skills section, keeping the resume's own groupings. "
        'Return ONLY JSON: {"skills": [{"category": "<group name>", '
        '"skills": ["<each item>"]}]}. List every single skill mentioned; '
        "do not summarise or drop any."
    ),
    "experience": (
        "Extract this ONE job role. Include EVERY achievement bullet listed "
        "for it, verbatim, in description. Return ONLY JSON: "
        '{"company", "title", "location", "start_date", "end_date", '
        '"current": bool, "description": ["<each bullet>"], '
        '"summary": "<one-line role context sentence if present>"}. '
        "Use null for unknown fields; end_date is null when it is the "
        "current role."
    ),
    "early_career": (
        "Extract EVERY earlier job role described in this text. For each, "
        "include every achievement bullet verbatim in description. Return "
        'ONLY JSON: {"experience": [{"company", "title", "location", '
        '"start_date", "end_date", "current": bool, "description": ["..."]}]}.'
    ),
    "education": (
        "Extract every qualification. Include every achievement bullet "
        "verbatim. Return ONLY JSON: {\"education\": [{\"institution\", "
        '"degree", "field", "start_date", "end_date", "gpa", '
        '"achievements": ["<each bullet>"]}]}.'
    ),
    "certifications": (
        "Extract EVERY certification, credential, and training item. Return "
        'ONLY JSON: {"certifications": [{"name", "issuer", "date", "url", '
        '"category", "values": []}]}. When the text groups items under a '
        "heading (e.g. \"Professional Credentials: A | B | C\"), emit one "
        "entry per named item with category set to the heading, AND one "
        "entry with category=heading and values=[all items]. Never drop an item."
    ),
    "awards": (
        "Extract EVERY award and recognition. Return ONLY JSON: "
        '{"awards": [{"name", "issuer", "date", "description"}]}. Include '
        "the year in name or date and the issuing organisation in issuer."
    ),
    "projects": (
        "Extract every project. Return ONLY JSON: {\"projects\": [{\"name\", "
        '"description", "url", "technologies": []}]}.'
    ),
    "languages": (
        "Extract every language. Return ONLY JSON: {\"languages\": [{\"name\", "
        '"proficiency"}]}.'
    ),
}

VERIFY_PROMPT = (
    "You are auditing a structured resume against its source text. Compare "
    "them and list any fact present in the source text but MISSING or "
    "ALTERED in the structured resume: job roles, bullet points, skills, "
    "certifications, awards, education details, dates, employers.\n\n"
    'Return ONLY JSON: {"missing": ["<the missing fact, verbatim>"]}. '
    "Return an empty list if nothing is missing."
)


def _coerce_list(value) -> list:
    if isinstance(value, list):
        return value
    if value in (None, "", {}):
        return []
    return [value]


async def parse_chunk(section: str, text: str, call) -> dict:
    """Parse one chunk into a partial dict. Returns {} when unusable."""
    instruction = CHUNK_PROMPTS.get(section, "Extract all resume facts. Return ONLY JSON.")
    system = f"You are a resume parser. {instruction}"
    try:
        raw = await call(system, text)
    except Exception as exc:  # noqa: BLE001 - one bad chunk must not kill the parse
        logger.warning("Chunk parse failed (section=%s): %s", section, exc)
        return {}
    if not raw:
        return {}
    try:
        data = json.loads(extract_json(raw))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Chunk output was not valid JSON (section=%s): %s", section, exc)
        return {}
    return data if isinstance(data, dict) else {}


def merge_chunks(results: list[tuple[str, dict]]) -> dict:
    """Combine per-section partial dicts into one resume-shaped dict."""
    merged: dict = {
        "experience": [],
        "education": [],
        "projects": [],
        "skills": [],
        "certifications": [],
        "awards": [],
        "languages": [],
    }
    for section, data in results:
        if not data:
            continue
        for key in ("full_name", "professional_title", "phone", "email", "location",
                    "linkedin", "github", "website", "summary"):
            value = data.get(key)
            if value not in (None, "", []):
                if isinstance(value, str):
                    value = value.strip()
                    if not value:
                        continue
                # A later chunk must not clobber real content with filler.
                if key == "summary" and merged.get(key):
                    continue
                merged[key] = value

        if section in ("experience", "early_career"):
            # A single-role chunk returns the role at the top level; a
            # multi-role chunk returns an "experience" list. Accept both so
            # one bad chunk shape cannot silently drop a job.
            raw_roles = data.get("experience")
            candidates = (
                _coerce_list(raw_roles)
                if raw_roles
                else ([{k: v for k, v in data.items() if k != "summary"}]
                      if data.get("company") and data.get("title") else [])
            )
            for item in candidates:
                if isinstance(item, dict) and item.get("company") and item.get("title"):
                    item["description"] = [
                        str(b) for b in _coerce_list(item.get("description")) if str(b).strip()
                    ]
                    merged["experience"].append(item)
        elif section == "education":
            for item in _coerce_list(data.get("education")):
                if isinstance(item, dict) and item.get("institution"):
                    item["achievements"] = [
                        str(a) for a in _coerce_list(item.get("achievements")) if str(a).strip()
                    ]
                    merged["education"].append(item)
        elif section == "certifications":
            for item in _coerce_list(data.get("certifications")):
                if isinstance(item, dict) and (item.get("name") or item.get("category")):
                    item["values"] = [str(v) for v in _coerce_list(item.get("values"))]
                    merged["certifications"].append(item)
        elif section == "awards":
            for item in _coerce_list(data.get("awards")):
                if isinstance(item, dict) and item.get("name"):
                    merged["awards"].append(item)
        elif section == "projects":
            for item in _coerce_list(data.get("projects")):
                if isinstance(item, dict) and item.get("name"):
                    merged["projects"].append(item)
        elif section == "languages":
            for item in _coerce_list(data.get("languages")):
                if isinstance(item, dict) and item.get("name"):
                    merged["languages"].append(item)
        elif section == "skills":
            for item in _coerce_list(data.get("skills")):
                if isinstance(item, dict) and item.get("category"):
                    item["skills"] = [str(s) for s in _coerce_list(item.get("skills"))]
                    merged["skills"].append(item)

    merged["experience"].sort(key=_sort_key)
    return merged


_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# Sorts after every real date, so undated entries fall to the end.
_NO_DATE = (9999, 12.31)


def _date_value(date: str | None) -> tuple[int, float]:
    """Sortable (year, month) from free-form date text; missing sorts last.

    Handles the many shapes a resume uses — "Jul 2026", "2026", "2026-07",
    "Present" — and returns a sentinel that sorts last when no year is found.
    """
    if not date or not isinstance(date, str):
        return _NO_DATE
    year = re.search(r"\b((?:19|20)\d{2})\b", date)
    if not year:
        return _NO_DATE
    month = 0.0
    for name, num in _MONTHS.items():
        if re.search(rf"\b{name}\b", date, re.I):
            month = num
            break
    return (int(year.group(1)), month)


def _sort_key(item: dict) -> tuple:
    """Present/ongoing roles first, then most recent, then oldest."""
    end = _date_value(item.get("end_date"))
    start = _date_value(item.get("start_date"))
    # A role with no end date, or one flagged current, is still running.
    if item.get("current") or end == _NO_DATE:
        return (0, -start[0], -start[1])
    return (1, -end[0], -end[1])


async def verify_completeness(source_text: str, resume_dict: dict, call) -> list[str]:
    """Ask the model which source facts the merged resume is missing."""
    payload = json.dumps(resume_dict, ensure_ascii=False)[:14000]
    prompt = (
        "SOURCE RESUME TEXT:\n"
        f"{source_text[:14000]}\n\n"
        "STRUCTURED RESUME:\n"
        f"{payload}\n\n"
        f"{VERIFY_PROMPT}"
    )
    try:
        raw = await call("You are a meticulous resume auditor.", prompt)
        data = json.loads(extract_json(raw or ""))
    except Exception as exc:  # noqa: BLE001 - audit is best-effort
        logger.info("Completeness audit skipped: %s", exc)
        return []
    missing = data.get("missing") if isinstance(data, dict) else None
    return [str(m) for m in _coerce_list(missing) if str(m).strip()]


def chunks_for(text: str) -> list[dict]:
    return chunk_resume(text)
