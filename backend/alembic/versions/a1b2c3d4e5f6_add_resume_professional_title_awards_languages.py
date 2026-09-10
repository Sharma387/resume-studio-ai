"""add_resume_professional_title_awards_languages

Revision ID: a1b2c3d4e5f6
Revises: e4f880195257
Create Date: 2026-08-09 12:00:00.000000

Adds professional_title, awards, and languages to the resumes table so the
full resume aggregate (title, projects, awards, languages) flows from parser →
domain model → database → repository → CVM → preview.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "e4f880195257"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("resumes", sa.Column("professional_title", sa.String(255), nullable=True))
    op.add_column(
        "resumes",
        sa.Column(
            "awards", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
    )
    op.add_column(
        "resumes",
        sa.Column(
            "languages", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
    )


def downgrade() -> None:
    op.drop_column("resumes", "languages")
    op.drop_column("resumes", "awards")
    op.drop_column("resumes", "professional_title")
