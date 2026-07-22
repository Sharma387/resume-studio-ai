import json
from pathlib import Path

from app.models.resume import Resume
from app.models.match import MatchResult
from app.models.version import ResumeVersion
from app.models.writer import ResumeSuggestion
from app.models.cover_letter import CoverLetter
from app.models.application import Application, TimelineEvent

RESUMES_DIR = Path("storage") / "resumes"
RESUMES_DIR.mkdir(parents=True, exist_ok=True)

MATCHES_DIR = Path("storage") / "matches"
MATCHES_DIR.mkdir(parents=True, exist_ok=True)

VERSIONS_DIR = Path("storage") / "versions"
VERSIONS_DIR.mkdir(parents=True, exist_ok=True)

WRITER_DIR = Path("storage") / "writer_suggestions"
WRITER_DIR.mkdir(parents=True, exist_ok=True)

COVER_LETTERS_DIR = Path("storage") / "cover_letters"
COVER_LETTERS_DIR.mkdir(parents=True, exist_ok=True)

APPLICATIONS_DIR = Path("storage") / "applications"
APPLICATIONS_DIR.mkdir(parents=True, exist_ok=True)

TIMELINE_DIR = Path("storage") / "timeline"
TIMELINE_DIR.mkdir(parents=True, exist_ok=True)

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


# ── Cover letter storage ───────────────────────────────────────


def save_cover_letter(letter: CoverLetter) -> None:
    dir_path = COVER_LETTERS_DIR / letter.resume_id
    dir_path.mkdir(parents=True, exist_ok=True)
    path = dir_path / f"{letter.id}.json"
    path.write_text(letter.model_dump_json(indent=2), encoding="utf-8")


def load_cover_letter(resume_id: str, letter_id: str) -> CoverLetter | None:
    path = COVER_LETTERS_DIR / resume_id / f"{letter_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return CoverLetter(**data)


def list_cover_letters(resume_id: str) -> list[CoverLetter]:
    dir_path = COVER_LETTERS_DIR / resume_id
    if not dir_path.exists():
        return []
    results = []
    for f in sorted(dir_path.iterdir(), reverse=True):
        if f.suffix == ".json":
            data = json.loads(f.read_text(encoding="utf-8"))
            results.append(CoverLetter(**data))
    return sorted(results, key=lambda c: c.created_at or "", reverse=True)


def delete_cover_letter(resume_id: str, letter_id: str) -> bool:
    path = COVER_LETTERS_DIR / resume_id / f"{letter_id}.json"
    if not path.exists():
        return False
    path.unlink()
    return True


# ── Application storage ───────────────────────────────────────


def save_application(app: Application) -> None:
    path = APPLICATIONS_DIR / f"{app.id}.json"
    path.write_text(app.model_dump_json(indent=2), encoding="utf-8")


def load_application(app_id: str) -> Application | None:
    path = APPLICATIONS_DIR / f"{app_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return Application(**data)


def list_applications(status: str | None = None) -> list[Application]:
    if not APPLICATIONS_DIR.exists():
        return []
    results = []
    for f in sorted(APPLICATIONS_DIR.iterdir(), reverse=True):
        if f.suffix == ".json":
            data = json.loads(f.read_text(encoding="utf-8"))
            app = Application(**data)
            if status is None or app.status.value == status:
                results.append(app)
    return sorted(results, key=lambda a: a.created_at or "", reverse=True)


def delete_application(app_id: str) -> bool:
    path = APPLICATIONS_DIR / f"{app_id}.json"
    if not path.exists():
        return False
    path.unlink()
    return True


# ── Timeline storage ───────────────────────────────────────


def save_timeline_event(event: TimelineEvent) -> None:
    dir_path = TIMELINE_DIR / event.application_id
    dir_path.mkdir(parents=True, exist_ok=True)
    path = dir_path / f"{event.id}.json"
    path.write_text(event.model_dump_json(indent=2), encoding="utf-8")


def list_timeline_events(application_id: str) -> list[TimelineEvent]:
    dir_path = TIMELINE_DIR / application_id
    if not dir_path.exists():
        return []
    results = []
    for f in sorted(dir_path.iterdir(), reverse=True):
        if f.suffix == ".json":
            data = json.loads(f.read_text(encoding="utf-8"))
            results.append(TimelineEvent(**data))
    return sorted(results, key=lambda e: e.created_at or "", reverse=True)
