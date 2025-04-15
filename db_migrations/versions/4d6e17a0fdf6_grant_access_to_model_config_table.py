"""grant access to model config table

Revision ID: 4d6e17a0fdf6
Revises: bf9021f32c31
Create Date: 2025-04-15 17:06:49.590191

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4d6e17a0fdf6"
down_revision: str | None = "bf9021f32c31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("GRANT USAGE ON SCHEMA model_config TO app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE model_config.model_config TO app")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("REVOKE USAGE ON SCHEMA model_config FROM app")
    op.execute("REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLE model_config.model_config FROM app")
