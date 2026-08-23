"""add_audit_log

Revision ID: e50d57dc9bc2
Revises: 722192dc02b1
Create Date: 2026-07-26 15:20:06.856224

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e50d57dc9bc2'
down_revision: Union[str, Sequence[str], None] = '722192dc02b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("timestamp", sa.String(32), nullable=False),
        sa.Column("admin_id", sa.String(32), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("target_user", sa.String(32), nullable=True),
        sa.Column("target_object", sa.String(255), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
    )
    op.create_index("ix_audit_log_timestamp", "audit_log", ["timestamp"])
    op.create_index("ix_audit_log_action", "audit_log", ["action"])
    op.create_index("ix_audit_log_admin_id", "audit_log", ["admin_id"])


def downgrade() -> None:
    op.drop_table("audit_log")
