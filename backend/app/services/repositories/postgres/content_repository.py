from datetime import UTC, datetime

from app.db.database import get_sync_session
from app.db.models.application import ApplicationModel, TimelineEventModel
from app.db.models.cover_letter import CoverLetterModel
from app.db.models.interview import (
    InterviewAnswerModel,
    InterviewQuestionModel,
    InterviewSessionModel,
    ReadinessAssessmentModel,
    SessionSummaryModel,
)
from app.db.models.match import MatchResultModel
from app.db.models.resume import ResumeModel
from app.db.models.version import ResumeVersionModel
from app.db.models.writer import WriterSuggestionModel
from app.models.application import Application, TimelineEvent
from app.models.cover_letter import CoverLetter
from app.models.interview import (
    InterviewAnswer,
    InterviewQuestion,
    InterviewSession,
    ReadinessAssessment,
    SessionSummary,
)
from app.models.match import MatchResult
from app.models.resume import Resume
from app.models.version import ResumeVersion
from app.models.writer import ResumeSuggestion
from app.services.repositories.interfaces import (
    ApplicationRepository,
    CoverLetterRepository,
    InterviewAnswerRepository,
    InterviewQuestionRepository,
    InterviewSessionRepository,
    MatchRepository,
    ReadinessAssessmentRepository,
    ResumeRepository,
    ResumeVersionRepository,
    SessionSummaryRepository,
    TimelineEventRepository,
    WriterSuggestionRepository,
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


# ── ResumeRepository ──────────────────────────────────────────────────────────


class PostgresResumeRepository(ResumeRepository):
    @staticmethod
    def _serialize_resume_sections(resume: Resume) -> dict:
        """Convert Resume Pydantic model to serializable dicts for JSONB columns."""

        def _serialize(obj):
            d = obj.model_dump()
            for k, v in d.items():
                if hasattr(v, "scheme"):
                    d[k] = str(v)
            return d

        return {
            "education": [_serialize(e) for e in resume.education],
            "experience": [_serialize(e) for e in resume.experience],
            "projects": [_serialize(p) for p in resume.projects],
            "skills": [_serialize(s) for s in resume.skills],
            "certifications": [_serialize(c) for c in resume.certifications],
            "awards": [_serialize(a) for a in resume.awards],
            "languages": [_serialize(lang) for lang in resume.languages],
        }

    def save(self, resume_id: str, resume: Resume) -> None:
        session = get_sync_session()
        try:
            sections = self._serialize_resume_sections(resume)
            existing = session.get(ResumeModel, resume_id)
            if existing:
                existing.full_name = resume.full_name
                existing.email = resume.email
                existing.phone = resume.phone
                existing.location = resume.location
                existing.linkedin = str(resume.linkedin) if resume.linkedin else None
                existing.github = str(resume.github) if resume.github else None
                existing.website = str(resume.website) if resume.website else None
                existing.summary = resume.summary
                existing.professional_title = resume.professional_title
                existing.education = sections["education"]
                existing.experience = sections["experience"]
                existing.projects = sections["projects"]
                existing.skills = sections["skills"]
                existing.certifications = sections["certifications"]
                existing.awards = sections["awards"]
                existing.languages = sections["languages"]
                existing.updated_at = _now()
            else:
                session.add(
                    ResumeModel(
                        id=resume_id,
                        user_id=resume.user_id,
                        full_name=resume.full_name,
                        email=resume.email,
                        phone=resume.phone,
                        location=resume.location,
                        linkedin=str(resume.linkedin) if resume.linkedin else None,
                        github=str(resume.github) if resume.github else None,
                        website=str(resume.website) if resume.website else None,
                        summary=resume.summary,
                        professional_title=resume.professional_title,
                        education=sections["education"],
                        experience=sections["experience"],
                        projects=sections["projects"],
                        skills=sections["skills"],
                        certifications=sections["certifications"],
                        awards=sections["awards"],
                        languages=sections["languages"],
                        created_at=_now(),
                        updated_at=_now(),
                    )
                )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_by_id(self, resume_id: str, user_id: str | None = None) -> Resume | None:
        session = get_sync_session()
        try:
            model = session.get(ResumeModel, resume_id)
            if model is None:
                return None
            if user_id is not None and model.user_id != user_id:
                return None
            return self._model_to_pydantic(model)
        finally:
            session.close()

    def list_by_user(self, user_id: str, limit: int = 10) -> list[tuple[str, Resume]]:
        session = get_sync_session()
        try:
            models = (
                session.query(ResumeModel)
                .filter(ResumeModel.user_id == user_id)
                .order_by(ResumeModel.created_at.desc())
                .limit(limit)
                .all()
            )
            return [(m.id, self._model_to_pydantic(m)) for m in models]
        finally:
            session.close()

    def _model_to_pydantic(self, m: ResumeModel) -> Resume:
        from pydantic import HttpUrl

        data = dict(
            user_id=m.user_id,
            full_name=m.full_name,
            email=m.email,
            phone=m.phone,
            location=m.location,
            linkedin=HttpUrl(m.linkedin) if m.linkedin else None,
            github=HttpUrl(m.github) if m.github else None,
            website=HttpUrl(m.website) if m.website else None,
            summary=m.summary,
            professional_title=m.professional_title,
            education=m.education or [],
            experience=m.experience or [],
            projects=m.projects or [],
            skills=m.skills or [],
            certifications=m.certifications or [],
            awards=m.awards or [],
            languages=m.languages or [],
        )
        return Resume(**data)


# ── ApplicationRepository ─────────────────────────────────────────────────────


class PostgresApplicationRepository(ApplicationRepository):
    def save(self, app: Application) -> None:
        session = get_sync_session()
        try:
            existing = session.get(ApplicationModel, app.id)
            if existing:
                for key in (
                    "company",
                    "role_title",
                    "location",
                    "url",
                    "status",
                    "priority",
                    "salary_range",
                    "resume_id",
                    "tags",
                    "last_activity",
                    "next_action",
                    "next_action_date",
                    "updated_at",
                ):
                    if hasattr(app, key):
                        setattr(existing, key, getattr(app, key))
            else:
                session.add(
                    ApplicationModel(
                        id=app.id,
                        user_id=app.user_id,
                        company=app.company,
                        role_title=app.role_title,
                        location=app.location,
                        url=app.url,
                        status=app.status.value if hasattr(app.status, "value") else app.status,
                        priority=app.priority.value if hasattr(app.priority, "value") else app.priority,
                        salary_range=app.salary_range,
                        resume_id=app.resume_id,
                        tags=app.tags,
                        last_activity=app.last_activity,
                        next_action=app.next_action,
                        next_action_date=app.next_action_date,
                        created_at=app.created_at or _now(),
                        updated_at=_now(),
                    )
                )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_by_id(self, app_id: str, user_id: str | None = None) -> Application | None:
        session = get_sync_session()
        try:
            model = session.get(ApplicationModel, app_id)
            if model is None:
                return None
            if user_id is not None and model.user_id != user_id:
                return None
            return self._model_to_pydantic(model)
        finally:
            session.close()

    def list_by_user(self, user_id: str | None = None, status: str | None = None) -> list[Application]:
        session = get_sync_session()
        try:
            q = session.query(ApplicationModel)
            if user_id is not None:
                q = q.filter(ApplicationModel.user_id == user_id)
            if status is not None:
                q = q.filter(ApplicationModel.status == status)
            models = q.order_by(ApplicationModel.created_at.desc()).all()
            return [self._model_to_pydantic(m) for m in models]
        finally:
            session.close()

    def delete(self, app_id: str, user_id: str | None = None) -> bool:
        session = get_sync_session()
        try:
            model = session.get(ApplicationModel, app_id)
            if model is None:
                return False
            if user_id is not None and model.user_id != user_id:
                return False
            session.delete(model)
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _model_to_pydantic(self, m: ApplicationModel) -> Application:
        return Application(
            id=m.id,
            user_id=m.user_id,
            company=m.company,
            role_title=m.role_title,
            location=m.location,
            url=m.url,
            status=m.status or "draft",
            priority=m.priority or "medium",
            salary_range=m.salary_range,
            resume_id=m.resume_id,
            tags=m.tags or [],
            notes=[],
            last_activity=m.last_activity,
            next_action=m.next_action,
            next_action_date=m.next_action_date,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )


# ── CoverLetterRepository ─────────────────────────────────────────────────────


class PostgresCoverLetterRepository(CoverLetterRepository):
    def save(self, letter: CoverLetter) -> None:
        session = get_sync_session()
        try:
            existing = session.get(CoverLetterModel, letter.id)
            if existing:
                for key in (
                    "company_name",
                    "hiring_manager",
                    "role_title",
                    "tone",
                    "content",
                    "subject",
                    "ai_model",
                    "job_description_hash",
                    "updated_at",
                ):
                    if hasattr(letter, key):
                        setattr(existing, key, getattr(letter, key))
            else:
                session.add(
                    CoverLetterModel(
                        id=letter.id,
                        user_id=letter.user_id,
                        resume_id=letter.resume_id,
                        application_id=letter.application_id,
                        company_name=letter.company_name,
                        hiring_manager=letter.hiring_manager,
                        role_title=letter.role_title,
                        tone=letter.tone.value if hasattr(letter.tone, "value") else (letter.tone or "professional"),
                        content=letter.content or "",
                        subject=letter.subject,
                        ai_model=letter.ai_model,
                        job_description_hash=letter.job_description_hash,
                        created_at=letter.created_at or _now(),
                        updated_at=_now(),
                    )
                )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_by_id(self, resume_id: str, letter_id: str, user_id: str | None = None) -> CoverLetter | None:
        session = get_sync_session()
        try:
            model = session.get(CoverLetterModel, letter_id)
            if model is None:
                return None
            if model.resume_id != resume_id:
                return None
            if user_id is not None and model.user_id != user_id:
                return None
            return self._model_to_pydantic(model)
        finally:
            session.close()

    def list_by_resume(self, resume_id: str, user_id: str | None = None) -> list[CoverLetter]:
        session = get_sync_session()
        try:
            q = session.query(CoverLetterModel).filter(CoverLetterModel.resume_id == resume_id)
            if user_id is not None:
                q = q.filter(CoverLetterModel.user_id == user_id)
            models = q.order_by(CoverLetterModel.created_at.desc()).all()
            return [self._model_to_pydantic(m) for m in models]
        finally:
            session.close()

    def delete(self, resume_id: str, letter_id: str, user_id: str | None = None) -> bool:
        session = get_sync_session()
        try:
            model = session.get(CoverLetterModel, letter_id)
            if model is None:
                return False
            if model.resume_id != resume_id:
                return False
            if user_id is not None and model.user_id != user_id:
                return False
            session.delete(model)
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _model_to_pydantic(self, m: CoverLetterModel) -> CoverLetter:
        return CoverLetter(
            id=m.id,
            user_id=m.user_id,
            resume_id=m.resume_id,
            application_id=m.application_id,
            company_name=m.company_name,
            hiring_manager=m.hiring_manager,
            role_title=m.role_title,
            tone=m.tone or "professional",
            content=m.content or "",
            subject=m.subject,
            ai_model=m.ai_model,
            job_description_hash=m.job_description_hash,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )


# ── MatchRepository ───────────────────────────────────────────────────────────


class PostgresMatchRepository(MatchRepository):
    def save(self, match_id: str, match: MatchResult) -> None:
        session = get_sync_session()
        try:
            existing = session.get(MatchResultModel, match_id)
            if existing:
                for key in (
                    "job_title",
                    "overall_score",
                    "skill_matches",
                    "matched_skills",
                    "missing_skills",
                    "recommendations",
                    "summary",
                ):
                    setattr(existing, key, getattr(match, key))
            else:
                session.add(
                    MatchResultModel(
                        id=match.id,
                        user_id=match.user_id,
                        resume_id=match.resume_id,
                        job_title=match.job_title,
                        overall_score=match.overall_score,
                        skill_matches=[s.model_dump() for s in match.skill_matches],
                        matched_skills=match.matched_skills,
                        missing_skills=match.missing_skills,
                        recommendations=[r.model_dump() for r in match.recommendations],
                        summary=match.summary,
                        created_at=match.created_at or _now(),
                    )
                )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_by_id(self, match_id: str, user_id: str | None = None) -> MatchResult | None:
        session = get_sync_session()
        try:
            model = session.get(MatchResultModel, match_id)
            if model is None:
                return None
            if user_id is not None and model.user_id != user_id:
                return None
            return self._model_to_pydantic(model)
        finally:
            session.close()

    def list_by_resume(self, resume_id: str, user_id: str | None = None) -> list[MatchResult]:
        session = get_sync_session()
        try:
            q = session.query(MatchResultModel).filter(MatchResultModel.resume_id == resume_id)
            if user_id is not None:
                q = q.filter(MatchResultModel.user_id == user_id)
            models = q.order_by(MatchResultModel.created_at.desc()).all()
            return [self._model_to_pydantic(m) for m in models]
        finally:
            session.close()

    def _model_to_pydantic(self, m: MatchResultModel) -> MatchResult:
        from app.models.match import Recommendation, SkillMatch

        return MatchResult(
            id=m.id,
            user_id=m.user_id,
            resume_id=m.resume_id,
            job_title=m.job_title,
            overall_score=m.overall_score,
            skill_matches=[SkillMatch(**s) for s in (m.skill_matches or [])],
            matched_skills=m.matched_skills or [],
            missing_skills=m.missing_skills or [],
            recommendations=[Recommendation(**r) for r in (m.recommendations or [])],
            summary=m.summary,
            created_at=m.created_at,
        )


# ── ResumeVersionRepository ──────────────────────────────────────────────────


class PostgresResumeVersionRepository(ResumeVersionRepository):
    def save(self, version: ResumeVersion) -> None:
        session = get_sync_session()
        try:
            section_data = PostgresResumeRepository._serialize_resume_sections(version.resume)
            resume_dict = version.resume.model_dump()
            resume_dict.update(section_data)
            for field in ("linkedin", "github", "website"):
                if resume_dict.get(field):
                    resume_dict[field] = str(resume_dict[field])
            session.add(
                ResumeVersionModel(
                    id=version.id,
                    user_id=version.user_id,
                    resume_id=version.resume_id,
                    label=version.label,
                    resume=resume_dict,
                    created_at=version.created_at or _now(),
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_by_id(self, resume_id: str, version_id: str, user_id: str | None = None) -> ResumeVersion | None:
        session = get_sync_session()
        try:
            model = session.get(ResumeVersionModel, version_id)
            if model is None:
                return None
            if model.resume_id != resume_id:
                return None
            if user_id is not None and model.user_id != user_id:
                return None
            return self._model_to_pydantic(model)
        finally:
            session.close()

    def list_by_resume(self, resume_id: str, user_id: str | None = None) -> list[ResumeVersion]:
        session = get_sync_session()
        try:
            q = session.query(ResumeVersionModel).filter(ResumeVersionModel.resume_id == resume_id)
            if user_id is not None:
                q = q.filter(ResumeVersionModel.user_id == user_id)
            models = q.order_by(ResumeVersionModel.created_at.desc()).all()
            return [self._model_to_pydantic(m) for m in models]
        finally:
            session.close()

    def _model_to_pydantic(self, m: ResumeVersionModel) -> ResumeVersion:
        return ResumeVersion(
            id=m.id,
            user_id=m.user_id,
            resume_id=m.resume_id,
            label=m.label,
            resume=Resume(**m.resume),
            created_at=m.created_at,
        )


# ── WriterSuggestionRepository ────────────────────────────────────────────────


class PostgresWriterSuggestionRepository(WriterSuggestionRepository):
    def save(self, suggestion: ResumeSuggestion) -> None:
        session = get_sync_session()
        try:
            session.add(
                WriterSuggestionModel(
                    id=suggestion.id,
                    user_id=suggestion.user_id,
                    resume_id=suggestion.resume_id,
                    suggestion_type=suggestion.suggestion_type,
                    section=suggestion.section,
                    field_path=suggestion.field_path,
                    original_text=suggestion.original_text or "",
                    suggested_text=suggestion.suggested_text or "",
                    reason=suggestion.reason or "",
                    confidence=suggestion.confidence,
                    ai_model=suggestion.ai_model,
                    source=suggestion.source or "ai_writer",
                    status=suggestion.status or "pending",
                    created_at=suggestion.created_at or _now(),
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_by_id(self, resume_id: str, suggestion_id: str, user_id: str | None = None) -> ResumeSuggestion | None:
        session = get_sync_session()
        try:
            model = session.get(WriterSuggestionModel, suggestion_id)
            if model is None:
                return None
            if model.resume_id != resume_id:
                return None
            if user_id is not None and model.user_id != user_id:
                return None
            return self._model_to_pydantic(model)
        finally:
            session.close()

    def list_by_resume(
        self, resume_id: str, status: str | None = None, user_id: str | None = None
    ) -> list[ResumeSuggestion]:
        session = get_sync_session()
        try:
            q = session.query(WriterSuggestionModel).filter(WriterSuggestionModel.resume_id == resume_id)
            if status is not None:
                q = q.filter(WriterSuggestionModel.status == status)
            if user_id is not None:
                q = q.filter(WriterSuggestionModel.user_id == user_id)
            models = q.order_by(WriterSuggestionModel.created_at.desc()).all()
            return [self._model_to_pydantic(m) for m in models]
        finally:
            session.close()

    def update(
        self, resume_id: str, suggestion_id: str, user_id: str | None = None, **updates
    ) -> ResumeSuggestion | None:
        session = get_sync_session()
        try:
            model = session.get(WriterSuggestionModel, suggestion_id)
            if model is None:
                return None
            if model.resume_id != resume_id:
                return None
            if user_id is not None and model.user_id != user_id:
                return None
            for key, value in updates.items():
                if hasattr(model, key):
                    setattr(model, key, value)
            session.commit()
            return self._model_to_pydantic(model)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _model_to_pydantic(self, m: WriterSuggestionModel) -> ResumeSuggestion:
        return ResumeSuggestion(
            id=m.id,
            user_id=m.user_id,
            resume_id=m.resume_id,
            suggestion_type=m.suggestion_type or "phrasing",
            section=m.section,
            field_path=m.field_path,
            original_text=m.original_text or "",
            suggested_text=m.suggested_text or "",
            reason=m.reason or "",
            confidence=m.confidence or 0.8,
            ai_model=m.ai_model,
            source=m.source or "ai_writer",
            status=m.status or "pending",
            created_at=m.created_at,
        )


# ── InterviewSessionRepository ────────────────────────────────────────────────


class PostgresInterviewSessionRepository(InterviewSessionRepository):
    def save(self, session: InterviewSession) -> None:
        s = get_sync_session()
        try:
            existing = s.get(InterviewSessionModel, session.id)
            if existing:
                for key in (
                    "title",
                    "session_type",
                    "question_count",
                    "readiness_score",
                    "duration_minutes",
                    "notes",
                    "completed",
                    "updated_at",
                ):
                    if hasattr(session, key):
                        setattr(existing, key, getattr(session, key))
            else:
                s.add(
                    InterviewSessionModel(
                        id=session.id,
                        user_id=session.user_id,
                        application_id=session.application_id,
                        plan_id=session.plan_id,
                        title=session.title or "",
                        session_type=session.session_type.value
                        if hasattr(session.session_type, "value")
                        else (session.session_type or "mock"),
                        question_count=session.question_count or 0,
                        readiness_score=session.readiness_score,
                        duration_minutes=session.duration_minutes,
                        notes=session.notes,
                        completed=session.completed or False,
                        created_at=session.created_at or _now(),
                        updated_at=_now(),
                    )
                )
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    def get_by_id(self, application_id: str, session_id: str, user_id: str | None = None) -> InterviewSession | None:
        s = get_sync_session()
        try:
            model = s.get(InterviewSessionModel, session_id)
            if model is None:
                return None
            if model.application_id != application_id:
                return None
            if user_id is not None and model.user_id != user_id:
                return None
            return self._model_to_pydantic(model)
        finally:
            s.close()

    def list_by_application(self, application_id: str, user_id: str | None = None) -> list[InterviewSession]:
        s = get_sync_session()
        try:
            q = s.query(InterviewSessionModel).filter(InterviewSessionModel.application_id == application_id)
            if user_id is not None:
                q = q.filter(InterviewSessionModel.user_id == user_id)
            models = q.order_by(InterviewSessionModel.created_at.desc()).all()
            return [self._model_to_pydantic(m) for m in models]
        finally:
            s.close()

    def delete(self, application_id: str, session_id: str) -> bool:
        s = get_sync_session()
        try:
            model = s.get(InterviewSessionModel, session_id)
            if model is None:
                return False
            if model.application_id != application_id:
                return False
            s.delete(model)
            s.commit()
            return True
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    def _model_to_pydantic(self, m: InterviewSessionModel) -> InterviewSession:
        return InterviewSession(
            id=m.id,
            user_id=m.user_id,
            application_id=m.application_id,
            plan_id=m.plan_id,
            title=m.title or "",
            session_type=m.session_type or "mock",
            question_count=m.question_count or 0,
            readiness_score=m.readiness_score,
            duration_minutes=m.duration_minutes,
            notes=m.notes,
            completed=m.completed or False,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )


# ── InterviewQuestionRepository ───────────────────────────────────────────────


class PostgresInterviewQuestionRepository(InterviewQuestionRepository):
    def save(self, question: InterviewQuestion) -> None:
        s = get_sync_session()
        try:
            s.add(
                InterviewQuestionModel(
                    id=question.id,
                    session_id=question.session_id,
                    question_type=question.question_type.value
                    if hasattr(question.question_type, "value")
                    else (question.question_type or "behavioral"),
                    question_text=question.question_text,
                    focus_area=question.focus_area,
                    tips=question.tips or [],
                    tags=question.tags or [],
                    difficulty=question.difficulty.value
                    if hasattr(question.difficulty, "value")
                    else (question.difficulty or "medium"),
                )
            )
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    def list_by_session(self, session_id: str) -> list[InterviewQuestion]:
        s = get_sync_session()
        try:
            models = s.query(InterviewQuestionModel).filter(InterviewQuestionModel.session_id == session_id).all()
            return [self._model_to_pydantic(m) for m in models]
        finally:
            s.close()

    def _model_to_pydantic(self, m: InterviewQuestionModel) -> InterviewQuestion:
        return InterviewQuestion(
            id=m.id,
            session_id=m.session_id,
            question_type=m.question_type or "behavioral",
            question_text=m.question_text,
            focus_area=m.focus_area,
            tips=m.tips or [],
            tags=m.tags or [],
            difficulty=m.difficulty or "medium",
        )


# ── InterviewAnswerRepository ─────────────────────────────────────────────────


class PostgresInterviewAnswerRepository(InterviewAnswerRepository):
    def save(self, answer: InterviewAnswer) -> None:
        s = get_sync_session()
        try:
            existing = s.get(InterviewAnswerModel, answer.id)
            if existing:
                for key in ("answer_type", "user_answer", "star_attempt", "feedback", "improved_answer", "score"):
                    setattr(existing, key, getattr(answer, key))
            else:
                s.add(
                    InterviewAnswerModel(
                        id=answer.id,
                        question_id=answer.question_id,
                        answer_type=answer.answer_type.value
                        if hasattr(answer.answer_type, "value")
                        else (answer.answer_type or "text"),
                        user_answer=answer.user_answer or "",
                        star_attempt=answer.star_attempt.model_dump()
                        if hasattr(answer.star_attempt, "model_dump")
                        else (answer.star_attempt or {}),
                        feedback=answer.feedback,
                        improved_answer=answer.improved_answer,
                        score=answer.score,
                        created_at=answer.created_at or _now(),
                    )
                )
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    def get_by_question(self, question_id: str) -> InterviewAnswer | None:
        s = get_sync_session()
        try:
            model = s.query(InterviewAnswerModel).filter(InterviewAnswerModel.question_id == question_id).first()
            if model is None:
                return None
            return self._model_to_pydantic(model)
        finally:
            s.close()

    def _model_to_pydantic(self, m: InterviewAnswerModel) -> InterviewAnswer:
        from app.models.interview import STARAttempt

        return InterviewAnswer(
            id=m.id,
            question_id=m.question_id,
            answer_type=m.answer_type or "text",
            user_answer=m.user_answer or "",
            star_attempt=STARAttempt(**(m.star_attempt or {})),
            feedback=m.feedback,
            improved_answer=m.improved_answer,
            score=m.score,
            created_at=m.created_at,
        )


# ── ReadinessAssessmentRepository ─────────────────────────────────────────────


class PostgresReadinessAssessmentRepository(ReadinessAssessmentRepository):
    def save(self, assessment: ReadinessAssessment) -> None:
        s = get_sync_session()
        try:
            s.add(
                ReadinessAssessmentModel(
                    id=assessment.id,
                    application_id=assessment.application_id,
                    overall_score=assessment.overall_score,
                    category_scores=assessment.category_scores or {},
                    strengths=assessment.strengths or [],
                    weaknesses=assessment.weaknesses or [],
                    recommendations=assessment.recommendations or [],
                    question_count=assessment.question_count or 0,
                    created_at=assessment.created_at or _now(),
                )
            )
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    def list_by_application(self, application_id: str) -> list[ReadinessAssessment]:
        s = get_sync_session()
        try:
            models = (
                s.query(ReadinessAssessmentModel)
                .filter(ReadinessAssessmentModel.application_id == application_id)
                .order_by(ReadinessAssessmentModel.created_at.desc())
                .all()
            )
            return [self._model_to_pydantic(m) for m in models]
        finally:
            s.close()

    def _model_to_pydantic(self, m: ReadinessAssessmentModel) -> ReadinessAssessment:
        return ReadinessAssessment(
            id=m.id,
            application_id=m.application_id,
            overall_score=m.overall_score,
            category_scores=m.category_scores or {},
            strengths=m.strengths or [],
            weaknesses=m.weaknesses or [],
            recommendations=m.recommendations or [],
            question_count=m.question_count or 0,
            created_at=m.created_at,
        )


# ── SessionSummaryRepository ──────────────────────────────────────────────────


class PostgresSessionSummaryRepository(SessionSummaryRepository):
    def save(self, summary: SessionSummary) -> None:
        s = get_sync_session()
        try:
            s.add(
                SessionSummaryModel(
                    id=summary.id,
                    session_id=summary.session_id,
                    application_id=summary.application_id,
                    total_questions=summary.total_questions or 0,
                    answered_questions=summary.answered_questions or 0,
                    average_score=summary.average_score,
                    strengths=summary.strengths or [],
                    areas_to_improve=summary.areas_to_improve or [],
                    recommendations=summary.recommendations or [],
                    created_at=summary.created_at or _now(),
                )
            )
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    def get_by_session(self, session_id: str) -> SessionSummary | None:
        s = get_sync_session()
        try:
            model = s.query(SessionSummaryModel).filter(SessionSummaryModel.session_id == session_id).first()
            if model is None:
                return None
            return self._model_to_pydantic(model)
        finally:
            s.close()

    def _model_to_pydantic(self, m: SessionSummaryModel) -> SessionSummary:
        return SessionSummary(
            id=m.id,
            session_id=m.session_id,
            application_id=m.application_id,
            total_questions=m.total_questions or 0,
            answered_questions=m.answered_questions or 0,
            average_score=m.average_score,
            strengths=m.strengths or [],
            areas_to_improve=m.areas_to_improve or [],
            recommendations=m.recommendations or [],
            created_at=m.created_at,
        )


# ── TimelineEventRepository ───────────────────────────────────────────────────


class PostgresTimelineEventRepository(TimelineEventRepository):
    def save(self, event: TimelineEvent) -> None:
        s = get_sync_session()
        try:
            s.add(
                TimelineEventModel(
                    id=event.id,
                    application_id=event.application_id,
                    event_type=event.event_type.value
                    if hasattr(event.event_type, "value")
                    else (event.event_type or "custom"),
                    title=event.title or "",
                    description=event.description or "",
                    event_metadata=event.metadata or {},
                    created_at=event.created_at or _now(),
                )
            )
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    def list_by_application(self, application_id: str) -> list[TimelineEvent]:
        s = get_sync_session()
        try:
            models = (
                s.query(TimelineEventModel)
                .filter(TimelineEventModel.application_id == application_id)
                .order_by(TimelineEventModel.created_at.desc())
                .all()
            )
            return [self._model_to_pydantic(m) for m in models]
        finally:
            s.close()

    def _model_to_pydantic(self, m: TimelineEventModel) -> TimelineEvent:
        return TimelineEvent(
            id=m.id,
            application_id=m.application_id,
            event_type=m.event_type or "custom",
            title=m.title or "",
            description=m.description or "",
            metadata=m.event_metadata or {},
            created_at=m.created_at,
        )
