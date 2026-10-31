from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import Conflict, NotFound
from app.enums import InvoiceStatus
from app.models import Invoice
from app.services.company import get_company
from app.services.invoice_pdf import invoice_filename, render_invoice_pdf
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
    company = get_company(db)
    send_mail(
        invoice.customer.email,
        f"Invoice {invoice.number} from {company.name}",
        f"Hello {invoice.customer.name},\n\nYour invoice {invoice.number} for INR {invoice.total:,.2f} is attached "
        f"as a PDF. {_balance_line(invoice)}\n\n{company.name}",
        attachments=[(invoice_filename(invoice), render_invoice_pdf(invoice, company), "application/pdf")],
    )
    invoice.sent_at = datetime.now(UTC)
    return invoice


def _balance_line(invoice: Invoice) -> str:
    """What the customer still has to do: nothing once it is paid, the balance after a part payment."""
    outstanding = invoice.total - invoice.amount_paid
    if invoice.status == InvoiceStatus.PAID or outstanding <= 0:
        return "It has been paid in full. Thank you, there is nothing more to pay."
    if invoice.amount_paid > 0:
        return (
            f"INR {invoice.amount_paid:,.2f} has been received; the remaining INR {outstanding:,.2f} is due on "
            f"{invoice.due_date:%d %b %Y}. You can view and pay it in the customer portal."
        )
    return f"It is due on {invoice.due_date:%d %b %Y}. You can also view and pay it in the customer portal."
