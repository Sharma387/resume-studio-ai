from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InterviewSessionModel(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    session_type: Mapped[str] = mapped_column(String(20), nullable=False, default="mock")
    question_count: Mapped[int] = mapped_column(nullable=False, default=0)
    readiness_score: Mapped[float | None] = mapped_column(nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=lambda: datetime.now(UTC).isoformat())
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False, default=lambda: datetime.now(UTC).isoformat())

    __table_args__ = (
        CheckConstraint("session_type IN ('mock','preparation','real_notes')", name="ck_interview_sessions_type"),
    )


class InterviewQuestionModel(Base):
    __tablename__ = "interview_questions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_type: Mapped[str] = mapped_column(String(20), nullable=False, default="behavioral")
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    focus_area: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tips: Mapped[list] = mapped_column(ARRAY(Text), nullable=False, default=list)
    tags: Mapped[list] = mapped_column(ARRAY(Text), nullable=False, default=list)
    difficulty: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")

    __table_args__ = (
        CheckConstraint(
            "question_type IN ('behavioral','technical','situational','role_specific','culture_fit')",
            name="ck_interview_questions_type",
        ),
        CheckConstraint("difficulty IN ('easy','medium','hard')", name="ck_interview_questions_difficulty"),
    )


class InterviewAnswerModel(Base):
    __tablename__ = "interview_answers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    question_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("interview_questions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    answer_type: Mapped[str] = mapped_column(String(10), nullable=False, default="text")
    user_answer: Mapped[str] = mapped_column(Text, nullable=False, default="")
    star_attempt: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    improved_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float | None] = mapped_column(nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=lambda: datetime.now(UTC).isoformat())


class ReadinessAssessmentModel(Base):
    __tablename__ = "readiness_assessments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    application_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    overall_score: Mapped[float] = mapped_column(nullable=False)
    category_scores: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    strengths: Mapped[list] = mapped_column(ARRAY(Text), nullable=False, default=list)
    weaknesses: Mapped[list] = mapped_column(ARRAY(Text), nullable=False, default=list)
    recommendations: Mapped[list] = mapped_column(ARRAY(Text), nullable=False, default=list)
    question_count: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=lambda: datetime.now(UTC).isoformat())


class SessionSummaryModel(Base):
    __tablename__ = "session_summaries"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    total_questions: Mapped[int] = mapped_column(nullable=False, default=0)
    answered_questions: Mapped[int] = mapped_column(nullable=False, default=0)
    average_score: Mapped[float | None] = mapped_column(nullable=True)
    strengths: Mapped[list] = mapped_column(ARRAY(Text), nullable=False, default=list)
    areas_to_improve: Mapped[list] = mapped_column(ARRAY(Text), nullable=False, default=list)
    recommendations: Mapped[list] = mapped_column(ARRAY(Text), nullable=False, default=list)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=lambda: datetime.now(UTC).isoformat())
