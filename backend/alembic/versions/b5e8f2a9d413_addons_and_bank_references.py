"""add-on products and bank statement references on payments

Revision ID: b5e8f2a9d413
Revises: a7b3d9e5c1f2
"""

import sqlalchemy as sa
from alembic import op

revision = "b5e8f2a9d413"
down_revision = "a7b3d9e5c1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("product", sa.Column("is_addon", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("payment", sa.Column("bank_ref", sa.String(length=64), nullable=True))
    op.create_unique_constraint("payment_bank_ref_key", "payment", ["bank_ref"])


def downgrade() -> None:
    op.drop_constraint("payment_bank_ref_key", "payment", type_="unique")
    op.drop_column("payment", "bank_ref")
    op.drop_column("product", "is_addon")
