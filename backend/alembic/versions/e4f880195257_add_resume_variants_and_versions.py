"""add_resume_variants_and_versions

Revision ID: e4f880195257
Revises: e50d57dc9bc2
Create Date: 2026-07-27 22:16:11.550011

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4f880195257"
down_revision: str | Sequence[str] | None = "e50d57dc9bc2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "resume_variants",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_id", sa.String(32), nullable=True),
        sa.Column("template_id", sa.String(64), nullable=False, server_default="executive-elite"),
        sa.Column("theme", sa.String(32), nullable=False, server_default="default"),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("layout", sa.String(32), nullable=False, server_default="single-column"),
        sa.Column("customization", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
    )
    op.create_index("ix_resume_variants_user_id", "resume_variants", ["user_id"])

    op.create_table(
        "resume_version_snapshots",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("variant_id", sa.String(32), sa.ForeignKey("resume_variants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_name", sa.String(255), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(32), nullable=False),
    )
    op.create_index("ix_resume_versions_variant_id", "resume_version_snapshots", ["variant_id"])


def downgrade() -> None:
    op.drop_table("resume_version_snapshots")
    op.drop_table("resume_variants")
