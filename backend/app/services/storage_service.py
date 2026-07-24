import json
from pathlib import Path

from app.models.resume import Resume
from app.models.match import MatchResult
from app.models.version import ResumeVersion
from app.models.writer import ResumeSuggestion
from app.models.cover_letter import CoverLetter
from app.models.application import Application, TimelineEvent
from app.models.interview import InterviewSession, InterviewQuestion, InterviewAnswer, ReadinessAssessment, SessionSummary

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

INTERVIEWS_DIR = Path("storage") / "interviews"
INTERVIEWS_DIR.mkdir(parents=True, exist_ok=True)

# ── Resume storage (unchanged) ──────────────────────────────────


def save_resume(resume_id: str, resume: Resume) -> None:
    path = RESUMES_DIR / f"{resume_id}.json"
    path.write_text(resume.model_dump_json(indent=2), encoding="utf-8")


def list_resumes(user_id: str | None = None, limit: int = 10) -> list[tuple[str, Resume]]:
    if not RESUMES_DIR.exists():
        return []
    results: list[tuple[str, Resume]] = []
    for f in sorted(RESUMES_DIR.iterdir(), reverse=True):
        if f.suffix == ".json":
            data = json.loads(f.read_text(encoding="utf-8"))
            resume = Resume(**data)
            if user_id and resume.user_id != user_id:
                continue
            results.append((f.stem, resume))
            if len(results) >= limit:
                break
    return results


def load_resume(resume_id: str, user_id: str | None = None) -> Resume | None:
    path = RESUMES_DIR / f"{resume_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    resume = Resume(**data)
    if user_id and resume.user_id != user_id:
        return None
    return resume

# ── Match result storage (new) ──────────────────────────────────


def save_match(match: MatchResult) -> None:
    path = MATCHES_DIR / f"{match.id}.json"
    path.write_text(match.model_dump_json(indent=2), encoding="utf-8")


def load_match(match_id: str, user_id: str | None = None) -> MatchResult | None:
    path = MATCHES_DIR / f"{match_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    match = MatchResult(**data)
    if user_id and match.user_id != user_id:
        return None
    return match


def list_matches(resume_id: str, user_id: str | None = None) -> list[MatchResult]:
    if not MATCHES_DIR.exists():
        return []
    results = []
    for f in MATCHES_DIR.iterdir():
        if f.suffix == ".json":
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("resume_id") == resume_id:
                match = MatchResult(**data)
                if user_id and match.user_id != user_id:
                    continue
                results.append(match)
    return sorted(results, key=lambda m: m.created_at or "", reverse=True)


# ── Version history storage ─────────────────────────────────────


def save_version(version: ResumeVersion) -> None:
    dir_path = VERSIONS_DIR / version.resume_id
    dir_path.mkdir(parents=True, exist_ok=True)
    path = dir_path / f"{version.id}.json"
    path.write_text(version.model_dump_json(indent=2), encoding="utf-8")


def load_version(resume_id: str, version_id: str, user_id: str | None = None) -> ResumeVersion | None:
    path = VERSIONS_DIR / resume_id / f"{version_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    version = ResumeVersion(**data)
    if user_id and version.user_id != user_id:
        return None
    return version


def list_versions(resume_id: str, user_id: str | None = None) -> list[ResumeVersion]:
    dir_path = VERSIONS_DIR / resume_id
    if not dir_path.exists():
        return []
    results = []
    for f in sorted(dir_path.iterdir(), reverse=True):
        if f.suffix == ".json":
            data = json.loads(f.read_text(encoding="utf-8"))
            version = ResumeVersion(**data)
            if user_id and version.user_id != user_id:
                continue
            results.append(version)
    return sorted(results, key=lambda v: v.created_at or "", reverse=True)


# ── Writer suggestion storage ───────────────────────────────────


def save_writer_suggestion(suggestion: ResumeSuggestion) -> None:
    dir_path = WRITER_DIR / suggestion.resume_id
    dir_path.mkdir(parents=True, exist_ok=True)
    path = dir_path / f"{suggestion.id}.json"
    path.write_text(suggestion.model_dump_json(indent=2), encoding="utf-8")


def load_writer_suggestion(resume_id: str, suggestion_id: str, user_id: str | None = None) -> ResumeSuggestion | None:
    path = WRITER_DIR / resume_id / f"{suggestion_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    sug = ResumeSuggestion(**data)
    if user_id and sug.user_id != user_id:
        return None
    return sug


def list_writer_suggestions(resume_id: str, status: str | None = None, user_id: str | None = None) -> list[ResumeSuggestion]:
    dir_path = WRITER_DIR / resume_id
    if not dir_path.exists():
        return []
    results = []
    for f in sorted(dir_path.iterdir(), reverse=True):
        if f.suffix == ".json":
            data = json.loads(f.read_text(encoding="utf-8"))
            s = ResumeSuggestion(**data)
            if user_id and s.user_id != user_id:
                continue
            if status is None or s.status == status:
                results.append(s)
    return results


def update_writer_suggestion(resume_id: str, suggestion_id: str, user_id: str | None = None, **updates) -> ResumeSuggestion | None:
    suggestion = load_writer_suggestion(resume_id, suggestion_id, user_id)
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


def load_cover_letter(resume_id: str, letter_id: str, user_id: str | None = None) -> CoverLetter | None:
    path = COVER_LETTERS_DIR / resume_id / f"{letter_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    letter = CoverLetter(**data)
    if user_id and letter.user_id != user_id:
        return None
    return letter


def list_cover_letters(resume_id: str, user_id: str | None = None) -> list[CoverLetter]:
    dir_path = COVER_LETTERS_DIR / resume_id
    if not dir_path.exists():
        return []
    results = []
    for f in sorted(dir_path.iterdir(), reverse=True):
        if f.suffix == ".json":
            data = json.loads(f.read_text(encoding="utf-8"))
            letter = CoverLetter(**data)
            if user_id and letter.user_id != user_id:
                continue
            results.append(letter)
    return sorted(results, key=lambda c: c.created_at or "", reverse=True)


def delete_cover_letter(resume_id: str, letter_id: str, user_id: str | None = None) -> bool:
    letter = load_cover_letter(resume_id, letter_id, user_id)
    if letter is None:
        return False
    path = COVER_LETTERS_DIR / resume_id / f"{letter_id}.json"
    path.unlink()
    return True


# ── Application storage ───────────────────────────────────────


def save_application(app: Application) -> None:
    path = APPLICATIONS_DIR / f"{app.id}.json"
    path.write_text(app.model_dump_json(indent=2), encoding="utf-8")


def load_application(app_id: str, user_id: str | None = None) -> Application | None:
    path = APPLICATIONS_DIR / f"{app_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    app = Application(**data)
    if user_id and app.user_id != user_id:
        return None
    return app


def list_applications(status: str | None = None, user_id: str | None = None) -> list[Application]:
    if not APPLICATIONS_DIR.exists():
        return []
    results = []
    for f in sorted(APPLICATIONS_DIR.iterdir(), reverse=True):
        if f.suffix == ".json":
            data = json.loads(f.read_text(encoding="utf-8"))
            app = Application(**data)
            if user_id and app.user_id != user_id:
                continue
            if status is None or app.status.value == status:
                results.append(app)
    return sorted(results, key=lambda a: a.created_at or "", reverse=True)


def delete_application(app_id: str, user_id: str | None = None) -> bool:
    app = load_application(app_id, user_id)
    if app is None:
        return False
    path = APPLICATIONS_DIR / f"{app_id}.json"
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


# ── Interview storage ───────────────────────────────────────


def _interview_subdir(application_id: str, sub: str) -> Path:
    d = INTERVIEWS_DIR / application_id / sub
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_interview_session(session: InterviewSession) -> None:
    path = _interview_subdir(session.application_id, "sessions") / f"{session.id}.json"
    path.write_text(session.model_dump_json(indent=2), encoding="utf-8")


def load_interview_session(application_id: str, session_id: str, user_id: str | None = None) -> InterviewSession | None:
    path = INTERVIEWS_DIR / application_id / "sessions" / f"{session_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    session = InterviewSession(**data)
    if user_id and session.user_id != user_id:
        return None
    return session


def list_interview_sessions(application_id: str, user_id: str | None = None) -> list[InterviewSession]:
    dir_path = INTERVIEWS_DIR / application_id / "sessions"
    if not dir_path.exists():
        return []
    results = []
    for f in sorted(dir_path.iterdir(), reverse=True):
        if f.suffix == ".json":
            data = json.loads(f.read_text(encoding="utf-8"))
            session = InterviewSession(**data)
            if user_id and session.user_id != user_id:
                continue
            results.append(session)
    return sorted(results, key=lambda s: s.created_at or "", reverse=True)


def delete_interview_session(application_id: str, session_id: str) -> bool:
    path = INTERVIEWS_DIR / application_id / "sessions" / f"{session_id}.json"
    if not path.exists():
        return False
    path.unlink()
    return True


def save_interview_question(question: InterviewQuestion) -> None:
    sdir = INTERVIEWS_DIR / question.session_id.split("-")[0] / "questions"
    sdir.mkdir(parents=True, exist_ok=True)
    path = sdir / f"{question.id}.json"
    path.write_text(question.model_dump_json(indent=2), encoding="utf-8")


def list_interview_questions(session_id: str) -> list[InterviewQuestion]:
    app_id = session_id.split("-")[0]
    dir_path = INTERVIEWS_DIR / app_id / "questions"
    if not dir_path.exists():
        return []
    results = []
    for f in dir_path.iterdir():
        if f.suffix == ".json":
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("session_id") == session_id:
                results.append(InterviewQuestion(**data))
    return results


def save_interview_answer(answer: InterviewAnswer) -> None:
    app_id = answer.question_id.split("-")[0]
    d = _interview_subdir(app_id, "answers")
    path = d / f"{answer.question_id}.json"
    path.write_text(answer.model_dump_json(indent=2), encoding="utf-8")


def load_interview_answer(question_id: str) -> InterviewAnswer | None:
    app_id = question_id.split("-")[0]
    path = INTERVIEWS_DIR / app_id / "answers" / f"{question_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return InterviewAnswer(**data)


def save_readiness_assessment(assessment: ReadinessAssessment) -> None:
    d = _interview_subdir(assessment.application_id, "readiness")
    path = d / f"{assessment.id}.json"
    path.write_text(assessment.model_dump_json(indent=2), encoding="utf-8")


def list_readiness_assessments(application_id: str) -> list[ReadinessAssessment]:
    dir_path = INTERVIEWS_DIR / application_id / "readiness"
    if not dir_path.exists():
        return []
    results = []
    for f in sorted(dir_path.iterdir(), reverse=True):
        if f.suffix == ".json":
            data = json.loads(f.read_text(encoding="utf-8"))
            results.append(ReadinessAssessment(**data))
    return sorted(results, key=lambda a: a.created_at or "", reverse=True)


def save_session_summary(summary: SessionSummary) -> None:
    d = _interview_subdir(summary.application_id, "summaries")
    path = d / f"{summary.session_id}.json"
    path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")


def load_session_summary(session_id: str) -> SessionSummary | None:
    app_id = session_id.split("-")[0]
    path = INTERVIEWS_DIR / app_id / "summaries" / f"{session_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return SessionSummary(**data)

