"""Owner: A — taxes and discounts."""

from datetime import date
from decimal import Decimal

from sqlalchemy import Column, Enum, ForeignKey, Index, Numeric, Table, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import AmountKind, DiscountScope
from app.models.base import Base, Money, Timestamp, utcnow
from app.models.catalog import Product
from app.models.subscriptions import Subscription

AmountKindType = Enum(AmountKind, name="amount_kind")  # shared by Tax and Discount

discount_products = Table(
    "discount_product",
    Base.metadata,
    Column("discount_id", ForeignKey("discount.id", ondelete="CASCADE"), primary_key=True),
    Column("product_id", ForeignKey("product.id", ondelete="CASCADE"), primary_key=True),
)

discount_subscriptions = Table(
    "discount_subscription",
    Base.metadata,
    Column("discount_id", ForeignKey("discount.id", ondelete="CASCADE"), primary_key=True),
    Column("subscription_id", ForeignKey("subscription.id", ondelete="CASCADE"), primary_key=True),
)


class Tax(Base):
    __tablename__ = "tax"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    kind: Mapped[AmountKind] = mapped_column(AmountKindType, default=AmountKind.PERCENT)
    rate: Mapped[Money]  # 18 = 18% when PERCENT; 18.00 per unit when FIXED
    active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    created_at: Mapped[Timestamp] = mapped_column(default=utcnow)


class Discount(Base):
    __tablename__ = "discount"
    __table_args__ = (Index("ix_discount_active_dates", "active", "start_date", "end_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    kind: Mapped[AmountKind] = mapped_column(AmountKindType)
    value: Mapped[Money]
    min_purchase: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    min_quantity: Mapped[int | None]
    start_date: Mapped[date]
    end_date: Mapped[date | None]
    usage_limit: Mapped[int | None]
    used_count: Mapped[int] = mapped_column(default=0)
    scope: Mapped[DiscountScope] = mapped_column(Enum(DiscountScope, name="discount_scope"))
    active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    created_at: Mapped[Timestamp] = mapped_column(default=utcnow)

    products: Mapped[list[Product]] = relationship(secondary=discount_products)
    subscriptions: Mapped[list[Subscription]] = relationship(secondary=discount_subscriptions)
