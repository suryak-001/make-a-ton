"""payment reminders, one per invoice per aging stage

Revision ID: f3a9c7d1b2e4
Revises: d4f1a7c2e9b6
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f3a9c7d1b2e4"
down_revision: str | None = "d4f1a7c2e9b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "invoice_reminder",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "invoice_id", sa.Integer(), sa.ForeignKey("invoice.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("stage", sa.String(length=16), nullable=False),
        sa.Column("sent_by_id", sa.Integer(), sa.ForeignKey("user.id", ondelete="SET NULL")),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("invoice_id", "stage"),
    )
    op.create_index("ix_invoice_reminder_invoice_id", "invoice_reminder", ["invoice_id"])


def downgrade() -> None:
    op.drop_index("ix_invoice_reminder_invoice_id", table_name="invoice_reminder")
    op.drop_table("invoice_reminder")
