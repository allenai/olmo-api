"""create model config schema

Revision ID: 35d1821c4d42
Revises: 4d6e17a0fdf6
Create Date: 2025-04-16 10:36:48.337340

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "35d1821c4d42"
down_revision: str | None = "67c7571bc5b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE SCHEMA model_config")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP SCHEMA model_config")
