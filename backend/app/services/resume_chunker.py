"""Split raw resume text into semantically-scoped chunks for AI parsing.

Local models run at a few tokens/second, so parsing a whole resume in one
call is impractical: the JSON for a multi-page resume runs 6-10K output
tokens, which takes tens of minutes and blows the model context window.
Chunking by section keeps each call's output small enough to finish
quickly and to fit the context, which is what makes complete capture
(roles, every bullet, certs, awards) achievable on modest hardware.

This module only *locates* sections — it extracts no resume content. Every
field is still produced by the AI from the chunk text, never by rules here.
"""

from __future__ import annotations

import re

# Section headings as they appear in resume text, mapped to the resume
# field they populate. Matched case-insensitively. Patterns that are
# "loose" (certification/award style headings that often carry a subtitle
# such as "CERTIFICATIONS & PROFESSIONAL DEVELOPMENT") are only honoured on
# lines that also LOOK like a standalone heading, so body prose is never
# mistaken for a section boundary.
_HEADING_PATTERNS: list[tuple[str, re.Pattern[str], bool]] = [
    ("summary", re.compile(r"^\s*(professional\s+)?(summary|profile|objective|about\s+me|career\s+summary)\s*:?\s*$", re.I), True),
    ("skills", re.compile(r"^\s*(core\s+)?(competenc\w*|technical\s+skills|skills|expertise|capabilit\w*)\b", re.I), True),
    ("experience", re.compile(r"^\s*(professional\s+|work\s+|employment|career|relevant\s+)?(experience|history|positions?)\s*:?\s*$", re.I), True),
    ("early_career", re.compile(r"^\s*(earlier|early|career\s+highlights?|additional\s+experience|previous\s+roles?)\b", re.I), True),
    ("education", re.compile(r"^\s*(education|academic|qualifications?)\s*:?\s*$", re.I), True),
    ("certifications", re.compile(r"^\s*(certificat\w*|licen[sc]\w*|training|professional\s+development|credentials?|courses?)\b", re.I), False),
    # "recognition" also takes a plural ("MAJOR RECOGNITIONS"), like the nouns
    # either side of it already did.
    ("awards", re.compile(r"^\s*(professional\s+)?(awards?|recognitions?|honou?rs?|achievements?)\b", re.I), False),
    # Qualified award headings: "KEY ACHIEVEMENTS", "SELECTED AWARDS",
    # "CAREER ACHIEVEMENTS", "MAJOR RECOGNITIONS". A leading qualifier defeats
    # the anchored pattern above, so those lines matched no heading at all and
    # their bullets were absorbed into the following section — on the real
    # resume that put five achievement bullets inside the skills chunk, where
    # the model then invented skill groups to hold them ("Project Delivery &
    # Achievement"). The qualifier is open-ended rather than a fixed word list
    # so the fix generalises, but it is only honoured on standalone heading
    # lines: allowing free text ahead of the noun on body prose would turn a
    # sentence into a section boundary.
    ("awards", re.compile(r"^\s*[A-Za-z][\w /&+.-]{0,30}?\s+(awards?|recognitions?|honou?rs?|achievements?)\b", re.I), True),
    ("projects", re.compile(r"^\s*(projects?|portfolio|selected\s+work)\s*:?\s*$", re.I), True),
    ("languages", re.compile(r"^\s*(languages?)\s*:?\s*$", re.I), True),
]

# A role header pairs a job title with an employer, e.g.
#   "Agile Delivery Lead  |  EBOS Group Limited"
#   "Project Manager, Datacom Systems Ltd"
#   "Senior Project Manager (Agile/Waterfall), Amadeus Software Labs, Bangalore"
# It must NOT look like a location/date line ("Auckland, New Zealand • Jul
# 2026 – Present") nor a bullet.
#
# Split in two because the separator determines how much the employer name can
# be trusted. A pipe or dash is unambiguous, so the name may start with any
# letter: "healthAlliance" and "iT" are ordinary company names, and missing one
# silently merged two roles into a single chunk — the model was then handed
# Datacom *and* healthAlliance together and returned only the second, losing a
# job with no error anywhere. A comma is weak, because it also appears in
# "Auckland, New Zealand" and in wrapped sentence text, so that form still
# requires a capitalised employer.
_ROLE_SPLIT_STRONG = re.compile(
    r"^[^•]{3,140}?(?:\s\|\s|\s—\s|\s–\s)\s*[A-Za-z][\w&.'\-() ]{2,70}$"
)
_ROLE_SPLIT_COMMA = re.compile(
    r"^[^•]{3,140}?,\s[A-Z][\w&.'\-() ]{2,70}$"
)


def _is_role_header(line: str) -> bool:
    return bool(_ROLE_SPLIT_STRONG.match(line) or _ROLE_SPLIT_COMMA.match(line))
# A trailing inline date range on a role header, e.g.
#   "Project Manager, NTT Data, Bangalore — 2003 to 2009"
# It is stripped before role-header matching so the trailing year doesn't stop
# the title/employer pattern from matching.
_TRAILING_DATES = re.compile(
    r"\s*(?:[—–-]|,)\s*"
    r"(?:(?:19|20)\d{2}(?:\s*(?:to|-|–|—)\s*(?:(?:19|20)\d{2}|Present|Current|Now))?)\s*$",
    re.I,
)
# A line that opens with a bullet marker. Resumes mix "•" and "-" styles, and
# a dash-bullet that happens to contain a comma ("... Animalcare, HPS and TWC
# ...") otherwise looks exactly like a "Title, Employer" role header, which
# would orphan the bullet into a chunk of its own and drop it.
_BULLET = re.compile(r"^\s*[-–—•*▪◦·]\s+")
# Lines that are location + date metadata, not role headers.
_META_LINE = re.compile(
    r"^\s*[^•]{0,60}(?:19|20)\d{2}\s*[-–—]\s*(?:(?:19|20)\d{2}|Present|Current|Now)\b",
    re.I,
)
# A bare location line ("Auckland, New Zealand") or a date range.
_DATE_RANGE = re.compile(r"^\s*(?:(?:19|20)\d{2}\s*[-–—]\s*(?:(?:19|20)\d{2}|Present|Current)|\w+\s+(?:19|20)\d{2})\s*$")

_HEADING_LOOKALIKE = re.compile(r"^\s*[A-Z][A-Z0-9 &/,'.\-()#]{3,70}\s*:?\s*$")


def _is_heading(line: str) -> str | None:
    """Return the section name this line is a heading for, if any.

    Patterns flagged as loose only match standalone-heading lines, which
    prevents body prose ("...delivering Program Increment commitments...")
    from opening a bogus section.
    """
    standalone = _looks_like_heading(line)
    for section, pattern, must_be_standalone in _HEADING_PATTERNS:
        if must_be_standalone and not standalone:
            continue
        if pattern.match(line):
            return section
    return None


def _looks_like_heading(line: str) -> bool:
    """ALL-CAPS standalone line, e.g. PROFESSIONAL SUMMARY."""
    s = line.strip()
    if not s or len(s) > 70:
        return False
    if s.count("•") or s.count("@"):
        return False
    return bool(_HEADING_LOOKALIKE.match(s))


def _split_experience(chunk_lines: list[str]) -> list[list[str]]:
    """Split an experience section into per-role blocks.

    A role block starts at a line that pairs a job title with an employer
    (containing a separator) and runs until the next such line. Bullets in any
    marker style always attach to the role above them, so they can never be
    mistaken for a role header. The first block may carry an untitled preamble
    (company description line), which stays with that role.
    """
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in chunk_lines:
        stripped = line.strip()
        is_role = False
        if stripped and not _BULLET.match(line):
            is_meta = bool(_META_LINE.match(stripped)) or bool(_DATE_RANGE.match(stripped))
            is_role = (not is_meta) and _is_role_header(_TRAILING_DATES.sub("", stripped))
        if is_role and current and any(c.strip() for c in current):
            blocks.append(current)
            current = [line]
        else:
            current.append(line)
    if current and any(c.strip() for c in current):
        blocks.append(current)
    return blocks


def chunk_resume(text: str, *, max_chars: int = 2600) -> list[dict]:
    """Return ordered chunks: ``[{"section": str, "text": str}, ...]``.

    ``section`` is one of header/summary/skills/experience/early_career/
    education/certifications/awards/projects/languages. Long sections are
    split further (experience per role, others by size) so no single AI
    call has to emit a large JSON document.
    """
    if not text or not text.strip():
        return []

    lines = text.splitlines()
    sections: list[tuple[str, int, int]] = []  # (name, start, end)
    current_name: str | None = None
    current_start = 0

    for i, line in enumerate(lines):
        matched = _is_heading(line)
        if matched is not None and matched != "header":
            if current_name is not None:
                sections.append((current_name, current_start, i))
            current_name, current_start = matched, i + 1

    if current_name is not None:
        sections.append((current_name, current_start, len(lines)))

    # Preamble before the first heading = name/contact header.
    if sections and sections[0][1] > 0:
        header_text = "\n".join(lines[: sections[0][1]]).strip()
        if header_text:
            sections.insert(0, ("header", 0, sections[0][1]))

    chunks: list[dict] = []
    for name, start, end in sections:
        body_lines = lines[start:end]
        # Trim the heading line itself out of the body. Only lines this module
        # recognised as a section heading may be dropped: a plain ALL-CAPS test
        # would also swallow the candidate's name, which is the single most
        # important field in the header section.
        while body_lines and _is_heading(body_lines[0]):
            body_lines.pop(0)
        while body_lines and not body_lines[0].strip():
            body_lines.pop(0)
        if not any(line.strip() for line in body_lines):
            continue
        body = "\n".join(body_lines).rstrip()

        if name in ("experience", "early_career"):
            for block in _split_experience(body_lines):
                block_text = "\n".join(block).strip()
                if block_text:
                    chunks.append({"section": name, "text": block_text})
            continue

        if len(body) <= max_chars:
            chunks.append({"section": name, "text": body})
            continue

        # Oversized free-form section: pack units up to max_chars so a bullet
        # is never cut in half. Units are blank-line-separated paragraphs, or
        # single lines when the section has no blank lines at all (common for
        # long bullet lists), which keeps every line intact either way.
        units = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
        if len(units) <= 1:
            units = [line for line in body.splitlines() if line.strip()]

        buf: list[str] = []
        size = 0
        for unit in units:
            if buf and size + len(unit) > max_chars:
                chunks.append({"section": name, "text": "\n".join(buf)})
                buf, size = [], 0
            buf.append(unit)
            size += len(unit) + 2
        if buf:
            chunks.append({"section": name, "text": "\n".join(buf)})

    return chunks
