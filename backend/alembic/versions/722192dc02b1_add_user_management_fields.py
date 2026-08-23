"""add_user_management_fields

Revision ID: 722192dc02b1
Revises: 34f537ca05d8
Create Date: 2026-07-26 14:55:30.207840

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '722192dc02b1'
down_revision: Union[str, Sequence[str], None] = '34f537ca05d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("users", sa.Column("disabled", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("users", sa.Column("last_login_at", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("last_password_change", sa.String(32), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "last_password_change")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "disabled")
    op.drop_column("users", "must_change_password")
