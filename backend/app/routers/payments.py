"""Payments recorded against confirmed invoices."""

from datetime import date

from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.deps import Db, StaffUser
from app.core.errors import Conflict
from app.core.pagination import Page, Pages, paginate
from app.enums import InvoiceStatus, PaymentMethod
from app.models import Invoice, Payment
from app.schemas.money import PaymentIn, PaymentOut
from app.services.invoice_queries import present_conditions
from app.services.invoices import get_invoice
from app.services.money_views import payment_out

router = APIRouter(prefix="/api/payments", tags=["payments"])

_LOAD = (joinedload(Payment.invoice).joinedload(Invoice.customer), joinedload(Payment.recorded_by))

_NOT_PAYABLE = {
    InvoiceStatus.DRAFT: "Confirm the invoice before recording a payment.",
    InvoiceStatus.PAID: "This invoice is already paid in full.",
    InvoiceStatus.CANCELLED: "A cancelled invoice can't take payments.",
}


@router.get("", response_model=Page[PaymentOut])
def list_payments(
    db: Db,
    _: StaffUser,
    pages: Pages,
    invoice_id: int | None = None,
    method: PaymentMethod | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
):
    conditions = present_conditions(
        (invoice_id, lambda v: Payment.invoice_id == v),
        (method, lambda v: Payment.method == v),
        (from_date, lambda v: Payment.payment_date >= v),
        (to_date, lambda v: Payment.payment_date <= v),
    )
    stmt = (
        select(Payment)
        .where(*conditions)
        .options(*_LOAD)
        .order_by(Payment.payment_date.desc(), Payment.id.desc())
    )
    rows, total = paginate(db, stmt, pages)
    return Page(items=[payment_out(p) for p in rows], total=total, page=pages.page, page_size=pages.page_size)


@router.post("", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(body: PaymentIn, db: Db, user: StaffUser):
    invoice = get_invoice(db, body.invoice_id, for_update=True)  # locked: two payments can't both fit
    _ensure_can_take(invoice, body)
    payment = Payment(**body.model_dump(), recorded_by_id=user.id)
    db.add(payment)
    invoice.amount_paid += body.amount
    if invoice.amount_paid >= invoice.total:
        invoice.status = InvoiceStatus.PAID
    db.commit()
    return payment_out(db.scalar(select(Payment).where(Payment.id == payment.id).options(*_LOAD)))


def _ensure_can_take(invoice: Invoice, payment: PaymentIn) -> None:
    if invoice.status != InvoiceStatus.CONFIRMED:
        raise Conflict(_NOT_PAYABLE[invoice.status])
    outstanding = invoice.total - invoice.amount_paid
    if payment.amount > outstanding:
        raise Conflict(f"Payment exceeds the outstanding amount of {outstanding}.")
