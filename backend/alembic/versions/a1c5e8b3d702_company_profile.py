"""company profile printed on invoices

Revision ID: a1c5e8b3d702
Revises: f3a9c7d1b2e4
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1c5e8b3d702"
down_revision: str | None = "f3a9c7d1b2e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "company_profile",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("tagline", sa.String()),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("phone", sa.String()),
        sa.Column("website", sa.String()),
        sa.Column("gstin", sa.String()),
        sa.Column("pan", sa.String()),
        sa.Column("bank_name", sa.String()),
        sa.Column("account_name", sa.String()),
        sa.Column("account_number", sa.String()),
        sa.Column("ifsc", sa.String()),
        sa.Column("upi_id", sa.String()),
        sa.Column("terms", sa.String()),
    )


def downgrade() -> None:
    op.drop_table("company_profile")
