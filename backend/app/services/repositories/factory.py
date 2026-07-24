"""Lightweight repository factory.

Returns JSON implementations by default.
Future: swap to PostgreSQL implementations by changing the factory.
"""

from app.services.repositories.interfaces import (
    ResumeRepository,
    ApplicationRepository,
    CoverLetterRepository,
    MatchRepository,
    ResumeVersionRepository,
    WriterSuggestionRepository,
    InterviewSessionRepository,
    TimelineEventRepository,
    InterviewQuestionRepository,
    InterviewAnswerRepository,
    ReadinessAssessmentRepository,
    SessionSummaryRepository,
)
from app.services.repositories.json.resume_repository import JsonResumeRepository
from app.services.repositories.json.application_repository import JsonApplicationRepository
from app.services.repositories.json.cover_letter_repository import JsonCoverLetterRepository
from app.services.repositories.json.match_repository import JsonMatchRepository
from app.services.repositories.json.version_repository import JsonResumeVersionRepository
from app.services.repositories.json.suggestion_repository import JsonWriterSuggestionRepository
from app.services.repositories.json.interview_repository import JsonInterviewSessionRepository, JsonInterviewQuestionRepository, JsonInterviewAnswerRepository, JsonReadinessAssessmentRepository, JsonSessionSummaryRepository
from app.services.repositories.json.timeline_repository import JsonTimelineEventRepository


def get_resume_repository() -> ResumeRepository:
    return JsonResumeRepository()


def get_application_repository() -> ApplicationRepository:
    return JsonApplicationRepository()


def get_cover_letter_repository() -> CoverLetterRepository:
    return JsonCoverLetterRepository()


def get_match_repository() -> MatchRepository:
    return JsonMatchRepository()


def get_version_repository() -> ResumeVersionRepository:
    return JsonResumeVersionRepository()


def get_suggestion_repository() -> WriterSuggestionRepository:
    return JsonWriterSuggestionRepository()


def get_interview_session_repository() -> InterviewSessionRepository:
    return JsonInterviewSessionRepository()


def get_timeline_event_repository() -> TimelineEventRepository:
    return JsonTimelineEventRepository()


def get_interview_question_repository() -> InterviewQuestionRepository:
    return JsonInterviewQuestionRepository()


def get_interview_answer_repository() -> InterviewAnswerRepository:
    return JsonInterviewAnswerRepository()


def get_readiness_assessment_repository() -> ReadinessAssessmentRepository:
    return JsonReadinessAssessmentRepository()


def get_session_summary_repository() -> SessionSummaryRepository:
    return JsonSessionSummaryRepository()
