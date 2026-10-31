"""demo payment gateway: orders, and the gateway's payment id on payments

Revision ID: d4f1a7c2e9b6
Revises: b5e8f2a9d413
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d4f1a7c2e9b6"
down_revision = "b5e8f2a9d413"
branch_labels = None
depends_on = None

order_status = postgresql.ENUM("CREATED", "PAID", "REFUND_DUE", name="gateway_order_status", create_type=False)
payment_method = postgresql.ENUM(name="payment_method", create_type=False)


def upgrade() -> None:
    order_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "gateway_order",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoice.id"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", order_status, nullable=False),
        sa.Column("payment_id", sa.String(length=32), nullable=True, unique=True),
        sa.Column("method", payment_method, nullable=True),
        sa.Column("instrument", sa.String(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("failure_reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_gateway_order_invoice_id", "gateway_order", ["invoice_id"])
    op.add_column("payment", sa.Column("gateway_payment_id", sa.String(length=32), nullable=True))
    op.create_unique_constraint("payment_gateway_payment_id_key", "payment", ["gateway_payment_id"])


def downgrade() -> None:
    op.drop_constraint("payment_gateway_payment_id_key", "payment", type_="unique")
    op.drop_column("payment", "gateway_payment_id")
    op.drop_index("ix_gateway_order_invoice_id", table_name="gateway_order")
    op.drop_table("gateway_order")
    order_status.drop(op.get_bind(), checkfirst=True)
