"""Owner: B — products, variants, plans, quotation templates."""

from datetime import date
from decimal import Decimal

from sqlalchemy import Column, Enum, ForeignKey, Integer, Table, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import BillingPeriod, ProductType
from app.models.base import Base, Money, Timestamp, utcnow

# Default taxes suggested for a product (the tax rows themselves are owned by B).
product_default_taxes = Table(
    "product_default_tax",
    Base.metadata,
    Column("product_id", ForeignKey("product.id", ondelete="CASCADE"), primary_key=True),
    Column("tax_id", ForeignKey("tax.id", ondelete="CASCADE"), primary_key=True),
)


class Product(Base):
    __tablename__ = "product"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    type: Mapped[ProductType] = mapped_column(
        Enum(ProductType, name="product_type"), default=ProductType.SERVICE
    )
    sales_price: Mapped[Money]
    cost_price: Mapped[Money] = mapped_column(default=Decimal("0"))
    notes: Mapped[str | None]
    active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    created_at: Mapped[Timestamp] = mapped_column(default=utcnow)

    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    default_taxes: Mapped[list["Tax"]] = relationship(secondary=product_default_taxes)  # noqa: F821


class ProductVariant(Base):
    __tablename__ = "product_variant"
    __table_args__ = (UniqueConstraint("product_id", "attribute", "value"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id", ondelete="CASCADE"))
    attribute: Mapped[str]  # e.g. "Brand"
    value: Mapped[str]  # e.g. "Odoo"
    extra_price: Mapped[Money] = mapped_column(default=Decimal("0"))  # e.g. 560

    product: Mapped[Product] = relationship(back_populates="variants")


class Plan(Base):
    __tablename__ = "plan"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    price: Mapped[Money]
    billing_period: Mapped[BillingPeriod] = mapped_column(Enum(BillingPeriod, name="billing_period"))
    min_quantity: Mapped[int] = mapped_column(Integer, default=1)
    available_from: Mapped[date | None]
    available_to: Mapped[date | None]
    # Per-plan behaviour, decided by the admin:
    auto_close: Mapped[bool] = mapped_column(default=False)  # close automatically at expiry
    closable: Mapped[bool] = mapped_column(default=True)  # can be closed early
    pausable: Mapped[bool] = mapped_column(default=False)
    renewable: Mapped[bool] = mapped_column(default=True)
    active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    created_at: Mapped[Timestamp] = mapped_column(default=utcnow)


class QuotationTemplate(Base):
    __tablename__ = "quotation_template"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    plan_id: Mapped[int] = mapped_column(ForeignKey("plan.id"))
    validity_days: Mapped[int] = mapped_column(default=30)
    notes: Mapped[str | None]
    created_at: Mapped[Timestamp] = mapped_column(default=utcnow)

    plan: Mapped[Plan] = relationship()
    lines: Mapped[list["QuotationTemplateLine"]] = relationship(
        back_populates="template", cascade="all, delete-orphan"
    )


class QuotationTemplateLine(Base):
    __tablename__ = "quotation_template_line"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("quotation_template.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"))
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variant.id"))
    quantity: Mapped[int] = mapped_column(default=1)

    template: Mapped[QuotationTemplate] = relationship(back_populates="lines")
    product: Mapped[Product] = relationship()
    variant: Mapped[ProductVariant | None] = relationship()
