"""cancelled invoices release their billing period

Revision ID: a7b3d9e5c1f2
Revises: e12c4f90a1b2
"""

import sqlalchemy as sa
from alembic import op

revision = "a7b3d9e5c1f2"
down_revision = "e12c4f90a1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_invoice_subscription_period", "invoice", type_="unique")
    op.create_index(
        "uq_invoice_subscription_period",
        "invoice",
        ["subscription_id", "period_start"],
        unique=True,
        postgresql_where=sa.text("status <> 'CANCELLED'"),
    )


def downgrade() -> None:
    # Fails if a period was re-billed (two rows for one period): cancel and remove the older one first.
    op.drop_index("uq_invoice_subscription_period", table_name="invoice")
    op.create_unique_constraint("uq_invoice_subscription_period", "invoice", ["subscription_id", "period_start"])
