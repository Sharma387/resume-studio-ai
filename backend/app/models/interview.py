from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class QuestionType(str, Enum):
    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"
    SITUATIONAL = "situational"
    ROLE_SPECIFIC = "role_specific"
    CULTURE_FIT = "culture_fit"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class AnswerType(str, Enum):
    TEXT = "text"
    AUDIO = "audio"
    VIDEO = "video"


class SessionType(str, Enum):
    MOCK = "mock"
    PREPARATION = "preparation"
    REAL_NOTES = "real_notes"


class InterviewSession(BaseModel):
    id: str = Field(..., min_length=1)
    application_id: str = Field(..., min_length=1)
    plan_id: str | None = Field(None, description="Future: multi-round interview plan")
    title: str = Field(default="")
    session_type: SessionType = SessionType.MOCK
    question_count: int = 0
    readiness_score: float | None = Field(None, ge=0.0, le=100.0)
    duration_minutes: int | None = None
    notes: str | None = None
    completed: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class STARAttempt(BaseModel):
    situation: str | None = None
    task: str | None = None
    action: str | None = None
    result: str | None = None


class InterviewQuestion(BaseModel):
    id: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    question_type: QuestionType = QuestionType.BEHAVIORAL
    question_text: str = Field(..., min_length=1)
    focus_area: str | None = None
    tips: list[str] = []
    tags: list[str] = []
    difficulty: Difficulty = Difficulty.MEDIUM


class InterviewAnswer(BaseModel):
    id: str = Field(..., min_length=1)
    question_id: str = Field(..., min_length=1)
    answer_type: AnswerType = AnswerType.TEXT
    user_answer: str = Field(default="")
    star_attempt: STARAttempt = Field(default_factory=STARAttempt)
    feedback: str | None = None
    improved_answer: str | None = None
    score: float | None = Field(None, ge=0.0, le=100.0)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ReadinessAssessment(BaseModel):
    id: str = Field(..., min_length=1)
    application_id: str = Field(..., min_length=1)
    overall_score: float = Field(..., ge=0.0, le=100.0)
    category_scores: dict = {}
    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations: list[str] = []
    question_count: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SessionSummary(BaseModel):
    id: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    application_id: str = Field(..., min_length=1)
    total_questions: int = 0
    answered_questions: int = 0
    average_score: float | None = None
    strengths: list[str] = []
    areas_to_improve: list[str] = []
    recommendations: list[str] = []
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
