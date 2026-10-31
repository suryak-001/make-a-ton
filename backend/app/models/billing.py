"""Owner: B — invoices, invoice lines, discount usage, payments."""

from datetime import date
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import InvoiceStatus, PaymentMethod
from app.models.base import Base, Money, Timestamp, utcnow
from app.models.identity import Customer, User
from app.models.rules import Discount
from app.models.subscriptions import Subscription


class Invoice(Base):
    __tablename__ = "invoice"
    __table_args__ = (
        # The "never bill twice" guarantee: one invoice per subscription per billing period.
        UniqueConstraint("subscription_id", "period_start", name="uq_invoice_subscription_period"),
        Index("ix_invoice_status_due_date", "status", "due_date"),
        Index("ix_invoice_customer_id", "customer_id"),
        Index("ix_invoice_invoice_date", "invoice_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(unique=True)  # INV-2026-00001
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscription.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.id"))
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status"), default=InvoiceStatus.DRAFT
    )
    period_start: Mapped[date]
    period_end: Mapped[date]
    invoice_date: Mapped[date]
    due_date: Mapped[date]
    subtotal: Mapped[Money]
    discount_total: Mapped[Money] = mapped_column(default=Decimal("0"))
    tax_total: Mapped[Money] = mapped_column(default=Decimal("0"))
    total: Mapped[Money]
    amount_paid: Mapped[Money] = mapped_column(default=Decimal("0"))
    sent_at: Mapped[Timestamp | None]
    created_at: Mapped[Timestamp] = mapped_column(default=utcnow)

    subscription: Mapped[Subscription] = relationship()
    customer: Mapped[Customer] = relationship()
    lines: Mapped[list["InvoiceLine"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(back_populates="invoice")


class InvoiceLine(Base):
    """Snapshot of the subscription line at billing time; later catalog edits don't change old invoices."""

    __tablename__ = "invoice_line"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoice.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("product.id", ondelete="SET NULL"))
    description: Mapped[str]
    quantity: Mapped[int]
    unit_price: Mapped[Money]
    discount_amount: Mapped[Money] = mapped_column(default=Decimal("0"))
    tax_amount: Mapped[Money] = mapped_column(default=Decimal("0"))
    total: Mapped[Money]

    invoice: Mapped[Invoice] = relationship(back_populates="lines")


class DiscountUsage(Base):
    __tablename__ = "discount_usage"
    __table_args__ = (UniqueConstraint("discount_id", "invoice_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    discount_id: Mapped[int] = mapped_column(ForeignKey("discount.id"))
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoice.id", ondelete="CASCADE"))
    created_at: Mapped[Timestamp] = mapped_column(default=utcnow)

    discount: Mapped[Discount] = relationship()


class Payment(Base):
    __tablename__ = "payment"
    __table_args__ = (
        Index("ix_payment_invoice_id", "invoice_id"),
        Index("ix_payment_payment_date", "payment_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoice.id"))
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod, name="payment_method"))
    amount: Mapped[Money]
    payment_date: Mapped[date]
    note: Mapped[str | None]
    recorded_by_id: Mapped[int | None] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"))
    created_at: Mapped[Timestamp] = mapped_column(default=utcnow)

    invoice: Mapped[Invoice] = relationship(back_populates="payments")
    recorded_by: Mapped[User | None] = relationship()
