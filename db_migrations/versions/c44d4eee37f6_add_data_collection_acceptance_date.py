"""add_data_collection_acceptance_date

Revision ID: c44d4eee37f6
Revises: b85b60aa5479
Create Date: 2025-07-08 13:01:15.197236

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c44d4eee37f6"
down_revision: str | None = "b85b60aa5479"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'olmo_user',
        sa.Column('data_collection_accepted_date', sa.TIMESTAMP(timezone=True), nullable=True)
    )
    op.add_column(
        'olmo_user',
        sa.Column(
            'data_collection_acceptance_revoked_date',
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment=(
                'GDPR requires that consent can be revoked. This field will allow us to track that '
                'while still keeping the user around. That may come in handy if we need to delete their data programmatically.'
            )
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('olmo_user', 'data_collection_acceptance_revoked_date')
    op.drop_column('olmo_user', 'data_collection_accepted_date')
