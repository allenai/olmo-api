"""make client unique

Revision ID: 8247ec761ef6
Revises: 20c0085a0629
Create Date: 2026-03-16 16:18:25.715359

"""

from typing import TYPE_CHECKING

from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "8247ec761ef6"
down_revision: str | None = "20c0085a0629"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index("client_idx", table_name="olmo_user")
    op.create_index(
        op.f("client_idx"),
        "olmo_user",
        ["client"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("client_idx"), table_name="olmo_user")
    op.create_index(
        "client_idx",
        "olmo_user",
        ["client"],
        unique=False,
    )
