import json
from pathlib import Path

from app.models.resume import Resume
from app.models.match import MatchResult
from app.models.version import ResumeVersion
from app.models.writer import ResumeSuggestion

RESUMES_DIR = Path("storage") / "resumes"
RESUMES_DIR.mkdir(parents=True, exist_ok=True)

MATCHES_DIR = Path("storage") / "matches"
MATCHES_DIR.mkdir(parents=True, exist_ok=True)

VERSIONS_DIR = Path("storage") / "versions"
VERSIONS_DIR.mkdir(parents=True, exist_ok=True)

WRITER_DIR = Path("storage") / "writer_suggestions"
WRITER_DIR.mkdir(parents=True, exist_ok=True)

# ── Resume storage (unchanged) ──────────────────────────────────


def save_resume(resume_id: str, resume: Resume) -> None:
    path = RESUMES_DIR / f"{resume_id}.json"
    path.write_text(resume.model_dump_json(indent=2), encoding="utf-8")


def load_resume(resume_id: str) -> Resume | None:
    path = RESUMES_DIR / f"{resume_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return Resume(**data)

# ── Match result storage (new) ──────────────────────────────────


def save_match(match: MatchResult) -> None:
    path = MATCHES_DIR / f"{match.id}.json"
    path.write_text(match.model_dump_json(indent=2), encoding="utf-8")


def load_match(match_id: str) -> MatchResult | None:
    path = MATCHES_DIR / f"{match_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return MatchResult(**data)


def list_matches(resume_id: str) -> list[MatchResult]:
    if not MATCHES_DIR.exists():
        return []
    results = []
    for f in MATCHES_DIR.iterdir():
        if f.suffix == ".json":
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("resume_id") == resume_id:
                results.append(MatchResult(**data))
    return sorted(results, key=lambda m: m.created_at or "", reverse=True)


# ── Version history storage ─────────────────────────────────────


def save_version(version: ResumeVersion) -> None:
    dir_path = VERSIONS_DIR / version.resume_id
    dir_path.mkdir(parents=True, exist_ok=True)
    path = dir_path / f"{version.id}.json"
    path.write_text(version.model_dump_json(indent=2), encoding="utf-8")


def load_version(resume_id: str, version_id: str) -> ResumeVersion | None:
    path = VERSIONS_DIR / resume_id / f"{version_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return ResumeVersion(**data)


def list_versions(resume_id: str) -> list[ResumeVersion]:
    dir_path = VERSIONS_DIR / resume_id
    if not dir_path.exists():
        return []
    results = []
    for f in sorted(dir_path.iterdir(), reverse=True):
        if f.suffix == ".json":
            data = json.loads(f.read_text(encoding="utf-8"))
            results.append(ResumeVersion(**data))
    return sorted(results, key=lambda v: v.created_at or "", reverse=True)


# ── Writer suggestion storage ───────────────────────────────────


def save_writer_suggestion(suggestion: ResumeSuggestion) -> None:
    dir_path = WRITER_DIR / suggestion.resume_id
    dir_path.mkdir(parents=True, exist_ok=True)
    path = dir_path / f"{suggestion.id}.json"
    path.write_text(suggestion.model_dump_json(indent=2), encoding="utf-8")


def load_writer_suggestion(resume_id: str, suggestion_id: str) -> ResumeSuggestion | None:
    path = WRITER_DIR / resume_id / f"{suggestion_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return ResumeSuggestion(**data)


def list_writer_suggestions(resume_id: str, status: str | None = None) -> list[ResumeSuggestion]:
    dir_path = WRITER_DIR / resume_id
    if not dir_path.exists():
        return []
    results = []
    for f in sorted(dir_path.iterdir(), reverse=True):
        if f.suffix == ".json":
            data = json.loads(f.read_text(encoding="utf-8"))
            s = ResumeSuggestion(**data)
            if status is None or s.status == status:
                results.append(s)
    return results


def update_writer_suggestion(resume_id: str, suggestion_id: str, **updates) -> ResumeSuggestion | None:
    suggestion = load_writer_suggestion(resume_id, suggestion_id)
    if suggestion is None:
        return None
    for key, value in updates.items():
        if hasattr(suggestion, key):
            setattr(suggestion, key, value)
    save_writer_suggestion(suggestion)
    return suggestion
