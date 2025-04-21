"""grant access to multi modal model config

Revision ID: f996e9be1bb0
Revises: 636b1b8f1f03
Create Date: 2025-04-18 17:14:41.082575

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f996e9be1bb0"
down_revision: str | None = "636b1b8f1f03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE multi_modal_model_config TO app")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLE multi_modal_model_config FROM app")
