from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.errors import NotFound
from app.enums import InvoiceStatus
from app.models import Invoice, Payment
from app.schemas.money import InvoiceOut, PaymentOut

INVOICE_LOAD = (
    joinedload(Invoice.customer),
    joinedload(Invoice.subscription),
    selectinload(Invoice.lines),
)


def invoice_out(invoice: Invoice, today: date | None = None) -> InvoiceOut:
    today = today or date.today()
    outstanding = max(invoice.total - invoice.amount_paid, Decimal("0"))
    return InvoiceOut(
        id=invoice.id,
        number=invoice.number,
        status=invoice.status,
        subscription={"id": invoice.subscription.id, "number": invoice.subscription.number},
        customer={"id": invoice.customer.id, "name": invoice.customer.name, "email": invoice.customer.email},
        period_start=invoice.period_start,
        period_end=invoice.period_end,
        invoice_date=invoice.invoice_date,
        due_date=invoice.due_date,
        subtotal=invoice.subtotal,
        discount_total=invoice.discount_total,
        tax_total=invoice.tax_total,
        total=invoice.total,
        amount_paid=invoice.amount_paid,
        outstanding=outstanding,
        overdue=invoice.status == InvoiceStatus.CONFIRMED and invoice.due_date < today and outstanding > 0,
        sent_at=invoice.sent_at,
        created_at=invoice.created_at,
        lines=invoice.lines,
    )


def load_invoice(db: Session, invoice_id: int) -> Invoice:
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id).options(*INVOICE_LOAD))
    if invoice is None:
        raise NotFound("Invoice not found.")
    return invoice


def payment_out(payment: Payment) -> PaymentOut:
    return PaymentOut(
        id=payment.id,
        invoice_id=payment.invoice_id,
        invoice_number=payment.invoice.number,
        customer_name=payment.invoice.customer.name,
        method=payment.method,
        amount=payment.amount,
        payment_date=payment.payment_date,
        note=payment.note,
        recorded_by=payment.recorded_by.name if payment.recorded_by else None,
        created_at=payment.created_at,
    )
