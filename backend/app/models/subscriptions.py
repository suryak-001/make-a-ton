"""Owner: A — subscriptions and their lines."""

from datetime import date

from sqlalchemy import Column, Enum, ForeignKey, Index, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import SubscriptionStatus
from app.models.base import Base, Money, Timestamp, utcnow
from app.models.catalog import Plan, Product, ProductVariant
from app.models.identity import Customer, User

subscription_line_taxes = Table(
    "subscription_line_tax",
    Base.metadata,
    Column("line_id", ForeignKey("subscription_line.id", ondelete="CASCADE"), primary_key=True),
    Column("tax_id", ForeignKey("tax.id", ondelete="CASCADE"), primary_key=True),
)


class Subscription(Base):
    __tablename__ = "subscription"
    __table_args__ = (
        Index("ix_subscription_status", "status"),
        Index("ix_subscription_customer_id", "customer_id"),
        Index("ix_subscription_status_next_invoice", "status", "next_invoice_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(unique=True)  # SUB-00001
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.id"))
    plan_id: Mapped[int] = mapped_column(ForeignKey("plan.id"))
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status"), default=SubscriptionStatus.DRAFT
    )
    start_date: Mapped[date]
    expiry_date: Mapped[date | None]
    payment_term_days: Mapped[int] = mapped_column(default=15)
    quotation_valid_until: Mapped[date | None]
    # Set when the subscription becomes ACTIVE; advanced by the billing run (B).
    next_invoice_date: Mapped[date | None]
    notes: Mapped[str | None]
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"))
    created_at: Mapped[Timestamp] = mapped_column(default=utcnow)
    updated_at: Mapped[Timestamp] = mapped_column(default=utcnow, onupdate=utcnow)

    customer: Mapped[Customer] = relationship()
    plan: Mapped[Plan] = relationship()
    created_by: Mapped[User | None] = relationship()
    lines: Mapped[list["SubscriptionLine"]] = relationship(
        back_populates="subscription", cascade="all, delete-orphan"
    )


class SubscriptionLine(Base):
    __tablename__ = "subscription_line"
    __table_args__ = (Index("ix_subscription_line_subscription_id", "subscription_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscription.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"))
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variant.id"))
    quantity: Mapped[int] = mapped_column(default=1)
    unit_price: Mapped[Money]  # product price + variant extra at time of quoting
    amount: Mapped[Money]  # computed via services.pricing

    subscription: Mapped[Subscription] = relationship(back_populates="lines")
    product: Mapped[Product] = relationship()
    variant: Mapped[ProductVariant | None] = relationship()
    taxes: Mapped[list["Tax"]] = relationship(secondary=subscription_line_taxes)  # noqa: F821
