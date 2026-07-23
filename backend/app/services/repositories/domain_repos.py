"""Domain-specific repositories — each only defines model class and storage path.

All CRUD behavior is inherited from JsonBaseRepository.
"""

from app.models.resume import Resume
from app.models.match import MatchResult
from app.models.cover_letter import CoverLetter
from app.models.application import Application
from app.models.interview import InterviewSession, ReadinessAssessment
from app.models.writer import ResumeSuggestion
from app.models.version import ResumeVersion
from app.models.notification import Notification
from app.services.repositories.json_base import JsonBaseRepository


class ResumeRepository(JsonBaseRepository[Resume]):
    model_class = Resume
    sub_dir = "resumes"


class MatchRepository(JsonBaseRepository[MatchResult]):
    model_class = MatchResult
    sub_dir = "matches"


class CoverLetterRepository(JsonBaseRepository[CoverLetter]):
    model_class = CoverLetter
    sub_dir = "cover_letters"


class ApplicationRepository(JsonBaseRepository[Application]):
    model_class = Application
    sub_dir = "applications"


class InterviewSessionRepository(JsonBaseRepository[InterviewSession]):
    model_class = InterviewSession
    sub_dir = "interviews/sessions"


class ReadinessAssessmentRepository(JsonBaseRepository[ReadinessAssessment]):
    model_class = ReadinessAssessment
    sub_dir = "interviews/readiness"


class ResumeSuggestionRepository(JsonBaseRepository[ResumeSuggestion]):
    model_class = ResumeSuggestion
    sub_dir = "writer_suggestions"


class ResumeVersionRepository(JsonBaseRepository[ResumeVersion]):
    model_class = ResumeVersion
    sub_dir = "versions"


class NotificationRepository(JsonBaseRepository[Notification]):
    model_class = Notification
    sub_dir = "notifications"
