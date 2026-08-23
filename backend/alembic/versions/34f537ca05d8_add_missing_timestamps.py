"""add_missing_timestamps

Revision ID: 34f537ca05d8
Revises: 0bfc78d2665a
Create Date: 2026-07-25 10:33:38.469293

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '34f537ca05d8'
down_revision: Union[str, Sequence[str], None] = '0bfc78d2665a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("applications", sa.Column("created_at", sa.String(32), nullable=False, server_default=""))
    op.add_column("applications", sa.Column("updated_at", sa.String(32), nullable=False, server_default=""))
    op.alter_column("applications", "created_at", server_default=None)
    op.alter_column("applications", "updated_at", server_default=None)


def downgrade() -> None:
    op.drop_column("applications", "updated_at")
    op.drop_column("applications", "created_at")
