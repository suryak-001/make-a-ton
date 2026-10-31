"""an admin can switch a staff member's access off

Revision ID: c8e3d1f5b204
Revises: b7d2c9e4a1f3
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c8e3d1f5b204"
down_revision: str | None = "b7d2c9e4a1f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column("user", "is_active")
