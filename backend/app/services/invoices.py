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


def confirm_invoice(db: Session, invoice_id: int) -> Invoice:
    invoice = get_invoice(db, invoice_id, for_update=True)
    if invoice.status != InvoiceStatus.DRAFT:
        raise Conflict("Only a draft invoice can be confirmed.")
    invoice.number = next_number(db, f"INV-{invoice.invoice_date.year}", f"INV-{invoice.invoice_date.year}-")
    invoice.status = InvoiceStatus.CONFIRMED
    return invoice


def cancel_invoice(db: Session, invoice_id: int) -> Invoice:
    invoice = get_invoice(db, invoice_id, for_update=True)
    if invoice.status not in {InvoiceStatus.DRAFT, InvoiceStatus.CONFIRMED}:
        raise Conflict("Only a draft or unpaid confirmed invoice can be cancelled.")
    if invoice.amount_paid > Decimal("0"):
        raise Conflict("An invoice with payments can't be cancelled.")
    invoice.status = InvoiceStatus.CANCELLED
    return invoice


def send_invoice(db: Session, invoice_id: int) -> Invoice:
    invoice = get_invoice(db, invoice_id)
    if invoice.status not in {InvoiceStatus.CONFIRMED, InvoiceStatus.PAID}:
        raise Conflict("Confirm the invoice before sending it.")
    send_mail(
        invoice.customer.email,
        f"Invoice {invoice.number}",
        f"Your invoice {invoice.number} totals {invoice.total}. Open the customer portal to view it.",
    )
    invoice.sent_at = datetime.now(UTC)
    return invoice
