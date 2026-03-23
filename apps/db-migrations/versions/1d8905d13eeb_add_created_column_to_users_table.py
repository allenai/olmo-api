"""add created column to users table

Revision ID: 1d8905d13eeb
Revises: 8247ec761ef6
Create Date: 2026-03-18 10:37:40.343269

"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "1d8905d13eeb"
down_revision: str | None = "8247ec761ef6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "olmo_user",
        sa.Column("created", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.execute("UPDATE olmo_user SET created = terms_accepted_date")
    op.alter_column("olmo_user", "created", nullable=False, server_default=sa.text("NOW()"))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("olmo_user", "created")
