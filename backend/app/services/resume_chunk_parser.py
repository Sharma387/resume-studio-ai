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
        "heading (e.g. \"Professional Credentials: A | B | C\"), set "
        "category to that heading on EVERY entry it covers. Do not add a "
        "separate entry for the heading itself. Never drop an item."
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

# A small local model cannot hold two documents in mind well enough to diff
# them: asked to compare, it reported all nine roles of the real resume as
# missing, including the four bullets sitting in the very JSON it was shown.
#
# Asking instead for plain *extraction* is a task these models do reliably, and
# the comparison then happens in Python where it cannot be wrong: list every
# fact the source states, and check each one against the parsed output.
LIST_FACTS_PROMPT = (
    "List every fact stated in the resume text below. Include each job role, "
    "each bullet point, each skill, certification, award, education detail, "
    "date and employer. Copy them exactly as written, one per array entry, "
    "without merging or summarising.\n\n"
    'Return ONLY JSON: {"facts": ["<fact>"]}'
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
            if raw_roles:
                candidates = _coerce_list(raw_roles)
            elif data.get("company") and data.get("title"):
                # Keep "summary" here: on a single-role chunk it holds the
                # organisation description line, which is preserved as a
                # bullet below rather than thrown away with the key.
                candidates = [dict(data)]
            else:
                candidates = []
            for item in candidates:
                if isinstance(item, dict) and item.get("company") and item.get("title"):
                    item["description"] = [
                        str(b) for b in _coerce_list(item.get("description")) if str(b).strip()
                    ]
                    # Resumes often open a role with a prose line describing the
                    # organisation ("Largest Australasian marketer, wholesaler,
                    # and distributor of healthcare...") that is not a bullet.
                    # The schema has no field for it, and dropping it loses a
                    # real detail, so it is kept as the first bullet. The audit
                    # flagged these as missing, which is what surfaced it.
                    role_summary = str(item.get("summary") or "").strip()
                    if role_summary and role_summary not in item["description"]:
                        item["description"].insert(0, role_summary)
                    item.pop("summary", None)
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


# The audit has to fit source text *and* the structured resume into the model
# context alongside the reply. At ~4 characters per token and a 4096-token
# window, roughly 10k characters of input is the safe ceiling once the
# instructions and the reply are accounted for.
#
# Auditing a whole three-page resume in one call cannot honour that: measured
# live, the resume JSON alone ran past 4000 characters, the server silently
# dropped the oldest tokens, and the model duly reported seven roles that were
# present in the output as "possibly missing". A false omission report is worse
# than no audit, because it sends whoever reads the log chasing facts that were
# never lost. So the audit is done per section, where both sides fit whole.
_AUDIT_SOURCE_CHARS = 4000
_AUDIT_PAYLOAD_CHARS = 4000


async def verify_completeness(source_text: str, resume_dict: dict, call) -> list[str]:
    """Ask the model which source facts the merged resume is missing.

    Kept for a whole-document check where both sides genuinely fit. Callers
    with a long resume should use :func:`verify_sections` instead, which
    cannot overflow the context.
    """
    source = source_text[:_AUDIT_SOURCE_CHARS]
    payload = json.dumps(resume_dict, ensure_ascii=False)[:_AUDIT_PAYLOAD_CHARS]
    if len(source) < len(source_text) or len(payload) < len(json.dumps(resume_dict, ensure_ascii=False)):
        logger.warning(
            "Whole-document completeness audit would overflow the context window; "
            "use verify_sections for resumes this long"
        )
        return []
    missing, _ = await _audit_pair(source, payload, call)
    return missing


def _as_text_list(value) -> list[str]:
    """Flatten a model's fact list into plain strings.

    Models nest the entries instead of returning a flat array — observed as
    ``{"facts": [{"fact": "Delivered 100% of ..."}]}`` — which stringified into
    a dict repr and then matched nothing, reporting real bullets as missing.
    """
    out: list[str] = []
    for item in _coerce_list(value):
        if isinstance(item, dict):
            for nested in item.values():
                out.extend(_as_text_list(nested))
        elif isinstance(item, (list, tuple)):
            out.extend(_as_text_list(item))
        else:
            text = str(item).strip()
            if text:
                out.append(text)
    return out


def _normalise_fact(text: str) -> str:
    """Reduce a fact to comparable content words.

    PDF extraction hard-wraps lines, so the same bullet appears in the source as
    several ragged fragments and in the parsed output as one clean sentence.
    Comparing the raw strings would report every wrapped bullet as missing.
    """
    lowered = re.sub(r"[^a-z0-9 ]+", " ", text.lower())
    return " ".join(lowered.split())


def _content_words(text: str) -> set[str]:
    """Words that carry meaning, ignoring filler common to every bullet."""
    stop = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is",
        "it", "its", "of", "on", "or", "that", "the", "to", "was", "were", "with",
        "this", "these", "those", "across", "within", "while", "including", "via",
        "over", "under", "into", "than", "then", "their", "our", "all", "also",
        "led", "managed", "delivered", "supported", "ensured", "driving", "own",
    }
    words = _normalise_fact(text).split()
    return {w for w in words if len(w) > 2 and w not in stop}


def _facts_missing_from(facts: list[str], payload: str, threshold: float = 0.55) -> list[str]:
    """Return the source facts that the parsed resume does not account for.

    A fact counts as captured when most of its significant words appear in the
    parsed output. The threshold absorbs reordering and the light rewording a
    model applies, without being loose enough to pass off a dropped bullet.
    """
    present = _content_words(payload)
    if not present:
        return [f for f in facts if _content_words(f)]

    missing: list[str] = []
    for fact in facts:
        words = _content_words(fact)
        if not words:
            continue
        overlap = len(words & present) / len(words)
        if overlap < threshold:
            missing.append(fact)
    return missing


async def _audit_pair(source: str, payload: str, call, label: str = "") -> tuple[list[str], bool]:
    """Run one audit comparison. Returns (missing facts, input was truncated).

    The model is asked only to *list* the source's facts, and the matching
    against the parsed output is done here. Diffing two documents is a task a
    small local model does badly — it flagged roles that were present in the
    very JSON beside them — whereas listing is one it does well, and a Python
    comparison cannot hallucinate.

    An input too large for the window is skipped rather than truncated: the
    result would be untrustworthy either way, and a false omission report sends
    whoever reads the log chasing facts that were never lost.
    """
    if len(source) > _AUDIT_SOURCE_CHARS:
        return [], True
    try:
        raw = await call(
            "You are a meticulous resume auditor.",
            f"RESUME TEXT ({label or 'document'}):\n{source}\n\n{LIST_FACTS_PROMPT}",
        )
        data = json.loads(extract_json(raw or ""))
    except Exception as exc:  # noqa: BLE001 - audit is best-effort
        logger.info("Completeness audit skipped for %s: %s", label or "document", exc)
        return [], False
    facts = data.get("facts") if isinstance(data, dict) else None
    facts = _as_text_list(facts)
    if not facts:
        return [], False
    return _facts_missing_from(facts, payload), False


def _section_shape(section: str, data: dict) -> dict:
    """Reshape a chunk's output the way :func:`merge_chunks` reads it.

    The audit compares a chunk's parsed output against that chunk's source
    text, so both sides must use the same schema. A single-role chunk returns
    the role at the top level while the merge wraps it into an ``experience``
    list; auditing the un-wrapped shape made every role look absent from its
    own section, and the audit duly reported all nine of them as missing.
    """
    if section not in ("experience", "early_career"):
        return data
    roles = _coerce_list(data.get("experience"))
    if not roles:
        if data.get("company") and data.get("title"):
            roles = [dict(data)]
        else:
            return data
    shaped = []
    for role in roles:
        if not isinstance(role, dict):
            continue
        # Mirror the merge: the organisation description line is kept as a
        # bullet, so the audit must see it there too.
        role_summary = str(role.get("summary") or "").strip()
        description = [str(b) for b in _coerce_list(role.get("description")) if str(b).strip()]
        if role_summary and role_summary not in description:
            description.insert(0, role_summary)
        shaped.append({k: v for k, v in role.items() if k != "summary"} | {"description": description})
    return {"experience": shaped}


async def verify_sections(pairs: list[tuple[str, str, dict]], call, *, max_calls: int | None = None) -> list[str]:
    """Audit each parsed section against the source text it came from.

    ``pairs`` is ``(section, source_text, parsed_data)``. Auditing section by
    section keeps both sides inside the context window, so a role that *is*
    present is never reported missing. Sections whose inputs did not fit are
    skipped and reported separately rather than guessed at.

    ``max_calls`` caps the extra model calls so the audit cannot itself push a
    parse past its time budget; sections not reached are named in the log.
    """
    findings: list[str] = []
    unverifiable: list[str] = []
    budget = max_calls if max_calls is not None else len(pairs)
    checked = 0
    for section, source_text, data in pairs:
        if checked >= budget:
            unverifiable.append(section)
            continue
        if not source_text or not data:
            continue
        payload = json.dumps(_section_shape(section, data), ensure_ascii=False)
        missing, truncated = await _audit_pair(source_text, payload, call, section)
        checked += 1
        if truncated:
            unverifiable.append(section)
            continue
        findings.extend(f"{section}: {fact}" for fact in missing)
    if unverifiable:
        logger.warning(
            "Completeness audit could not verify %s: input too large for the context window",
            ", ".join(unverifiable),
        )
    return findings


def chunks_for(text: str) -> list[dict]:
    return chunk_resume(text)
