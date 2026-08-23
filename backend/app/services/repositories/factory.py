"""Lightweight repository factory.

Returns JSON or PostgreSQL implementations based on STORAGE_BACKEND.
"""

from app.core.config import settings
from app.core.logging import get_logger
from app.services.repositories.interfaces import (
    ApplicationRepository,
    CoverLetterRepository,
    InterviewAnswerRepository,
    InterviewQuestionRepository,
    InterviewSessionRepository,
    MatchRepository,
    ReadinessAssessmentRepository,
    RefreshTokenRepository,
    ResumeRepository,
    ResumeVersionRepository,
    SessionSummaryRepository,
    TimelineEventRepository,
    UserRepository,
    VariantRepository,
    WriterSuggestionRepository,
)
from app.services.repositories.json.application_repository import JsonApplicationRepository
from app.services.repositories.json.cover_letter_repository import JsonCoverLetterRepository
from app.services.repositories.json.interview_repository import (
    JsonInterviewAnswerRepository,
    JsonInterviewQuestionRepository,
    JsonInterviewSessionRepository,
    JsonReadinessAssessmentRepository,
    JsonSessionSummaryRepository,
)
from app.services.repositories.json.match_repository import JsonMatchRepository
from app.services.repositories.json.resume_repository import JsonResumeRepository
from app.services.repositories.json.suggestion_repository import JsonWriterSuggestionRepository
from app.services.repositories.json.timeline_repository import JsonTimelineEventRepository
from app.services.repositories.json.variant_repository import JsonVariantRepository
from app.services.repositories.json.version_repository import JsonResumeVersionRepository
from app.services.repositories.json_token_repo import JsonRefreshTokenRepository
from app.services.repositories.json_user_repo import JsonUserRepository
from app.services.repositories.postgres.content_repository import (
    PostgresApplicationRepository,
    PostgresCoverLetterRepository,
    PostgresInterviewAnswerRepository,
    PostgresInterviewQuestionRepository,
    PostgresInterviewSessionRepository,
    PostgresMatchRepository,
    PostgresReadinessAssessmentRepository,
    PostgresResumeRepository,
    PostgresResumeVersionRepository,
    PostgresSessionSummaryRepository,
    PostgresTimelineEventRepository,
    PostgresWriterSuggestionRepository,
)
from app.services.repositories.postgres.token_repository import PostgresRefreshTokenRepository
from app.services.repositories.postgres.user_repository import PostgresUserRepository
from app.services.repositories.postgres.variant_repository import PostgresVariantRepository

logger = get_logger(__name__)


def _use_json() -> bool:
    return settings.storage_backend == "json"


def _log_repo(name: str, backend: str) -> None:
    logger.debug("Repository selected", repo=name, backend=backend)


def get_user_repository() -> UserRepository:
    if _use_json():
        return JsonUserRepository()
    _log_repo("UserRepository", "postgres")
    return PostgresUserRepository()


def get_refresh_token_repository() -> RefreshTokenRepository:
    if _use_json():
        return JsonRefreshTokenRepository()
    _log_repo("RefreshTokenRepository", "postgres")
    return PostgresRefreshTokenRepository()


def get_resume_repository() -> ResumeRepository:
    if _use_json():
        return JsonResumeRepository()
    _log_repo("ResumeRepository", "postgres")
    return PostgresResumeRepository()


def get_variant_repository() -> VariantRepository:
    if _use_json():
        return JsonVariantRepository()
    _log_repo("VariantRepository", "postgres")
    return PostgresVariantRepository()


def get_application_repository() -> ApplicationRepository:
    if _use_json():
        return JsonApplicationRepository()
    _log_repo("ApplicationRepository", "postgres")
    return PostgresApplicationRepository()


def get_cover_letter_repository() -> CoverLetterRepository:
    if _use_json():
        return JsonCoverLetterRepository()
    _log_repo("CoverLetterRepository", "postgres")
    return PostgresCoverLetterRepository()


def get_match_repository() -> MatchRepository:
    if _use_json():
        return JsonMatchRepository()
    _log_repo("MatchRepository", "postgres")
    return PostgresMatchRepository()


def get_version_repository() -> ResumeVersionRepository:
    if _use_json():
        return JsonResumeVersionRepository()
    _log_repo("ResumeVersionRepository", "postgres")
    return PostgresResumeVersionRepository()


def get_suggestion_repository() -> WriterSuggestionRepository:
    if _use_json():
        return JsonWriterSuggestionRepository()
    _log_repo("WriterSuggestionRepository", "postgres")
    return PostgresWriterSuggestionRepository()


def get_interview_session_repository() -> InterviewSessionRepository:
    if _use_json():
        return JsonInterviewSessionRepository()
    _log_repo("InterviewSessionRepository", "postgres")
    return PostgresInterviewSessionRepository()


def get_timeline_event_repository() -> TimelineEventRepository:
    if _use_json():
        return JsonTimelineEventRepository()
    _log_repo("TimelineEventRepository", "postgres")
    return PostgresTimelineEventRepository()


def get_interview_question_repository() -> InterviewQuestionRepository:
    if _use_json():
        return JsonInterviewQuestionRepository()
    _log_repo("InterviewQuestionRepository", "postgres")
    return PostgresInterviewQuestionRepository()


def get_interview_answer_repository() -> InterviewAnswerRepository:
    if _use_json():
        return JsonInterviewAnswerRepository()
    _log_repo("InterviewAnswerRepository", "postgres")
    return PostgresInterviewAnswerRepository()


def get_readiness_assessment_repository() -> ReadinessAssessmentRepository:
    if _use_json():
        return JsonReadinessAssessmentRepository()
    _log_repo("ReadinessAssessmentRepository", "postgres")
    return PostgresReadinessAssessmentRepository()


def get_session_summary_repository() -> SessionSummaryRepository:
    if _use_json():
        return JsonSessionSummaryRepository()
    _log_repo("SessionSummaryRepository", "postgres")
    return PostgresSessionSummaryRepository()
