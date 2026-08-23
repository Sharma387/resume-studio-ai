"""add_remaining_tables

Revision ID: 0bfc78d2665a
Revises: 93b139268152
Create Date: 2026-07-25 10:19:03.443334

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0bfc78d2665a'
down_revision: Union[str, Sequence[str], None] = '93b139268152'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resumes",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50)),
        sa.Column("location", sa.String(255)),
        sa.Column("linkedin", sa.String(500)),
        sa.Column("github", sa.String(500)),
        sa.Column("website", sa.String(500)),
        sa.Column("summary", sa.Text),
        sa.Column("education", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("experience", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("projects", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("skills", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("certifications", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
    )
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"])

    op.create_table(
        "applications",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("role_title", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255)),
        sa.Column("url", sa.Text),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("priority", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("salary_range", sa.String(100)),
        sa.Column("resume_id", sa.String(32), sa.ForeignKey("resumes.id", ondelete="SET NULL")),
        sa.Column("tags", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("last_activity", sa.String(32)),
        sa.Column("next_action", sa.Text),
        sa.Column("next_action_date", sa.String(32)),
        sa.CheckConstraint("status IN ('draft','applied','screening','interviewing','offered','rejected','withdrawn','accepted','archived')", name="ck_applications_status"),
        sa.CheckConstraint("priority IN ('low','medium','high')", name="ck_applications_priority"),
    )
    op.create_index("ix_applications_user_id", "applications", ["user_id"])
    op.create_index("ix_applications_resume_id", "applications", ["resume_id"])

    op.create_table(
        "interview_sessions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", sa.String(32), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", sa.String(32)),
        sa.Column("title", sa.String(255), nullable=False, server_default=""),
        sa.Column("session_type", sa.String(20), nullable=False, server_default="mock"),
        sa.Column("question_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("readiness_score", sa.Float()),
        sa.Column("duration_minutes", sa.Integer()),
        sa.Column("notes", sa.Text),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
        sa.CheckConstraint("session_type IN ('mock','preparation','real_notes')", name="ck_interview_sessions_type"),
    )
    op.create_index("ix_interview_sessions_user_id", "interview_sessions", ["user_id"])
    op.create_index("ix_interview_sessions_application_id", "interview_sessions", ["application_id"])

    op.create_table(
        "cover_letters",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_id", sa.String(32), sa.ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", sa.String(32), sa.ForeignKey("applications.id", ondelete="SET NULL")),
        sa.Column("company_name", sa.String(255)),
        sa.Column("hiring_manager", sa.String(255)),
        sa.Column("role_title", sa.String(255)),
        sa.Column("tone", sa.String(20), nullable=False, server_default="professional"),
        sa.Column("content", sa.Text, nullable=False, server_default=""),
        sa.Column("subject", sa.Text),
        sa.Column("ai_model", sa.String(100)),
        sa.Column("job_description_hash", sa.String(16)),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
        sa.CheckConstraint("tone IN ('professional','enthusiastic','formal','concise')", name="ck_cover_letters_tone"),
    )
    op.create_index("ix_cover_letters_user_id", "cover_letters", ["user_id"])
    op.create_index("ix_cover_letters_resume_id", "cover_letters", ["resume_id"])
    op.create_index("ix_cover_letters_application_id", "cover_letters", ["application_id"])

    op.create_table(
        "match_results",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_id", sa.String(32), sa.ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_title", sa.String(255)),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("skill_matches", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("matched_skills", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("missing_skills", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("recommendations", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("summary", sa.Text),
        sa.Column("created_at", sa.String(32), nullable=False),
    )
    op.create_index("ix_match_results_user_id", "match_results", ["user_id"])
    op.create_index("ix_match_results_resume_id", "match_results", ["resume_id"])

    op.create_table(
        "resume_versions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_id", sa.String(32), sa.ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(255)),
        sa.Column("resume", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(32), nullable=False),
    )
    op.create_index("ix_resume_versions_user_id", "resume_versions", ["user_id"])
    op.create_index("ix_resume_versions_resume_id", "resume_versions", ["resume_id"])

    op.create_table(
        "writer_suggestions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_id", sa.String(32), sa.ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("suggestion_type", sa.String(50), nullable=False, server_default="phrasing"),
        sa.Column("section", sa.String(255), nullable=False),
        sa.Column("field_path", sa.Text),
        sa.Column("original_text", sa.Text, nullable=False, server_default=""),
        sa.Column("suggested_text", sa.Text, nullable=False, server_default=""),
        sa.Column("reason", sa.Text, nullable=False, server_default=""),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("ai_model", sa.String(100)),
        sa.Column("source", sa.String(50), nullable=False, server_default="ai_writer"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.CheckConstraint("status IN ('pending','accepted','rejected')", name="ck_writer_suggestions_status"),
    )
    op.create_index("ix_writer_suggestions_user_id", "writer_suggestions", ["user_id"])
    op.create_index("ix_writer_suggestions_resume_id", "writer_suggestions", ["resume_id"])

    op.create_table(
        "timeline_events",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("application_id", sa.String(32), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False, server_default="custom"),
        sa.Column("title", sa.String(255), nullable=False, server_default=""),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.String(32), nullable=False),
    )
    op.create_index("ix_timeline_events_application_id", "timeline_events", ["application_id"])

    op.create_table(
        "application_notes",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("application_id", sa.String(32), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.String(32), nullable=False),
    )
    op.create_index("ix_application_notes_application_id", "application_notes", ["application_id"])

    op.create_table(
        "interview_questions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("session_id", sa.String(32), sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_type", sa.String(20), nullable=False, server_default="behavioral"),
        sa.Column("question_text", sa.Text, nullable=False),
        sa.Column("focus_area", sa.String(255)),
        sa.Column("tips", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("tags", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("difficulty", sa.String(10), nullable=False, server_default="medium"),
        sa.CheckConstraint("question_type IN ('behavioral','technical','situational','role_specific','culture_fit')", name="ck_interview_questions_type"),
        sa.CheckConstraint("difficulty IN ('easy','medium','hard')", name="ck_interview_questions_difficulty"),
    )
    op.create_index("ix_interview_questions_session_id", "interview_questions", ["session_id"])

    op.create_table(
        "interview_answers",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("question_id", sa.String(32), sa.ForeignKey("interview_questions.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("answer_type", sa.String(10), nullable=False, server_default="text"),
        sa.Column("user_answer", sa.Text, nullable=False, server_default=""),
        sa.Column("star_attempt", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("feedback", sa.Text),
        sa.Column("improved_answer", sa.Text),
        sa.Column("score", sa.Float()),
        sa.Column("created_at", sa.String(32), nullable=False),
    )
    op.create_index("ix_interview_answers_question_id", "interview_answers", ["question_id"])

    op.create_table(
        "readiness_assessments",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("application_id", sa.String(32), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("category_scores", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("strengths", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("weaknesses", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("recommendations", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("question_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.String(32), nullable=False),
    )
    op.create_index("ix_readiness_assessments_application_id", "readiness_assessments", ["application_id"])

    op.create_table(
        "session_summaries",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("session_id", sa.String(32), sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", sa.String(32), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("total_questions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("answered_questions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("average_score", sa.Float()),
        sa.Column("strengths", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("areas_to_improve", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("recommendations", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.String(32), nullable=False),
    )
    op.create_index("ix_session_summaries_session_id", "session_summaries", ["session_id"])
    op.create_index("ix_session_summaries_application_id", "session_summaries", ["application_id"])


def downgrade() -> None:
    op.drop_table("session_summaries")
    op.drop_table("readiness_assessments")
    op.drop_table("interview_answers")
    op.drop_table("interview_questions")
    op.drop_table("application_notes")
    op.drop_table("timeline_events")
    op.drop_table("writer_suggestions")
    op.drop_table("resume_versions")
    op.drop_table("match_results")
    op.drop_table("cover_letters")
    op.drop_table("interview_sessions")
    op.drop_table("applications")
    op.drop_table("resumes")
