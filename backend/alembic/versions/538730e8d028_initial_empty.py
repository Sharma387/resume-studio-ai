"""initial_empty

Revision ID: 538730e8d028
Revises:
Create Date: 2026-07-25 01:02:43.555653

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "538730e8d028"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
