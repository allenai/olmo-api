"""init from existing table

Revision ID: 67c7571bc5b8
Revises:
Create Date: 2025-04-15 17:21:58.254593

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "67c7571bc5b8"
down_revision: str | None = "4d6e17a0fdf6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with open("./schema/schema.sql", encoding="utf-8") as schema_file:
        query = schema_file.read()
        op.execute(query)


def downgrade() -> None:
    """Downgrade schema."""
