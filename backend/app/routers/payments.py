"""Payments recorded against confirmed invoices."""

from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.deps import Db, StaffUser
from app.core.errors import Conflict
from app.core.pagination import Page, Pages, paginate
from app.enums import InvoiceStatus
from app.models import Invoice, Payment
from app.schemas.money import PaymentIn, PaymentOut
from app.services.invoices import get_invoice
from app.services.money_views import payment_out

router = APIRouter(prefix="/api/payments", tags=["payments"])

_LOAD = (joinedload(Payment.invoice).joinedload(Invoice.customer), joinedload(Payment.recorded_by))


@router.get("", response_model=Page[PaymentOut])
def list_payments(db: Db, _: StaffUser, pages: Pages, invoice_id: int | None = None):
    stmt = select(Payment).options(*_LOAD).order_by(Payment.payment_date.desc(), Payment.id.desc())
    if invoice_id:
        stmt = stmt.where(Payment.invoice_id == invoice_id)
    rows, total = paginate(db, stmt, pages)
    return Page(items=[payment_out(p) for p in rows], total=total, page=pages.page, page_size=pages.page_size)


@router.post("", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(body: PaymentIn, db: Db, user: StaffUser):
    invoice = get_invoice(db, body.invoice_id, for_update=True)
    if invoice.status != InvoiceStatus.CONFIRMED:
        raise Conflict("Payments can only be recorded against a confirmed invoice.")
    outstanding = invoice.total - invoice.amount_paid
    if body.amount > outstanding:
        raise Conflict(f"Payment exceeds the outstanding amount of {outstanding}.")
    payment = Payment(**body.model_dump(), recorded_by_id=user.id)
    db.add(payment)
    invoice.amount_paid += body.amount
    if invoice.amount_paid >= invoice.total:
        invoice.status = InvoiceStatus.PAID
    db.commit()
    payment = db.scalar(select(Payment).where(Payment.id == payment.id).options(*_LOAD))
    return payment_out(payment)
