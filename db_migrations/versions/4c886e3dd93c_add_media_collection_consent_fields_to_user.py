"""add_media_collection_consent_fields_to_user

Revision ID: 4c886e3dd93c
Revises: edaadce92f0a
Create Date: 2025-12-09 16:21:37.596631

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4c886e3dd93c"
down_revision: str | None = "edaadce92f0a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "olmo_user",
        sa.Column("media_collection_accepted_date", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "olmo_user",
        sa.Column("media_collection_acceptance_revoked_date", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("olmo_user", "media_collection_acceptance_revoked_date")
    op.drop_column("olmo_user", "media_collection_accepted_date")
