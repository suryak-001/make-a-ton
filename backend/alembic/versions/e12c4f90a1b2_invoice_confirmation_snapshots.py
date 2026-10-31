"""invoice confirmation numbering and tax snapshots

Revision ID: e12c4f90a1b2
Revises: dc91514db0c0
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e12c4f90a1b2"
down_revision: str | None = "dc91514db0c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("invoice", "number", existing_type=sa.String(), nullable=True)
    op.add_column(
        "invoice_line",
        sa.Column("tax_rate", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
    )
    op.alter_column("invoice_line", "tax_rate", server_default=None)


def downgrade() -> None:
    op.drop_column("invoice_line", "tax_rate")
    op.alter_column("invoice", "number", existing_type=sa.String(), nullable=False)
