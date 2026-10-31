"""staff added by an admin must choose their own password on first sign-in

Revision ID: b7d2c9e4a1f3
Revises: a1c5e8b3d702
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7d2c9e4a1f3"
down_revision: str | None = "a1c5e8b3d702"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user", sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("user", "must_change_password")
