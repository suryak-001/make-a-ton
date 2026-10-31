from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import Conflict, NotFound
from app.enums import InvoiceStatus
from app.models import Invoice
from app.services.mail import send_mail
from app.services.sequence import next_number


def get_invoice(db: Session, invoice_id: int, *, for_update: bool = False) -> Invoice:
    stmt = select(Invoice).where(Invoice.id == invoice_id)
    if for_update:
        stmt = stmt.with_for_update()
    else:
        stmt = stmt.options(joinedload(Invoice.customer))
    invoice = db.scalar(stmt)
    if invoice is None:
        raise NotFound("Invoice not found.")
    return invoice


# What may be done to an invoice. The server checks these and also tells the UI, so both always agree.
REFUSALS = {
    "confirm": "Only a draft invoice can be confirmed.",
    "cancel": "Only a draft invoice, or a confirmed one with no payments, can be cancelled.",
    "send": "Confirm the invoice before sending it.",
}


def allowed_actions(invoice: Invoice) -> list[str]:
    if invoice.status == InvoiceStatus.DRAFT:
        return ["confirm", "cancel"]
    if invoice.status == InvoiceStatus.CONFIRMED:
        unpaid = invoice.amount_paid == Decimal("0")
        return ["pay", "send", "print", *(["cancel"] if unpaid else [])]
    if invoice.status == InvoiceStatus.PAID:
        return ["send", "print"]
    # Cancelled: the period can be billed again, by an admin (the route enforces that; the screen hides it).
    return ["rebill"]


def _require(invoice: Invoice, action: str) -> None:
    if action not in allowed_actions(invoice):
        raise Conflict(REFUSALS[action])


def confirm_invoice(db: Session, invoice_id: int) -> Invoice:
    invoice = get_invoice(db, invoice_id, for_update=True)
    _require(invoice, "confirm")
    year = invoice.invoice_date.year
    invoice.number = next_number(db, f"INV-{year}", f"INV-{year}-")
    invoice.status = InvoiceStatus.CONFIRMED
    return invoice


def cancel_invoice(db: Session, invoice_id: int) -> Invoice:
    invoice = get_invoice(db, invoice_id, for_update=True)
    _require(invoice, "cancel")
    invoice.status = InvoiceStatus.CANCELLED
    return invoice


def send_invoice(db: Session, invoice_id: int) -> Invoice:
    invoice = get_invoice(db, invoice_id)
    _require(invoice, "send")
    send_mail(
        invoice.customer.email,
        f"Invoice {invoice.number}",
        f"Your invoice {invoice.number} totals {invoice.total}. Open the customer portal to view it.",
    )
    invoice.sent_at = datetime.now(UTC)
    return invoice
