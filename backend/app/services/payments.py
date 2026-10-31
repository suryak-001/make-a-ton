"""Recording a payment against an invoice. The payments screen, bank reconciliation and the online checkout all
come through here."""

from sqlalchemy.orm import Session

from app.core.errors import Conflict
from app.enums import InvoiceStatus
from app.models import Invoice, Payment, User
from app.schemas.money import PaymentIn
from app.services.invoices import get_invoice

_NOT_PAYABLE = {
    InvoiceStatus.DRAFT: "Confirm the invoice before recording a payment.",
    InvoiceStatus.PAID: "This invoice is already paid in full.",
    InvoiceStatus.CANCELLED: "A cancelled invoice can't take payments.",
}


def record_payment(
    db: Session,
    body: PaymentIn,
    user: User | None,
    *,
    bank_ref: str | None = None,
    gateway_payment_id: str | None = None,
) -> Payment:
    """Partial payments are fine, overpayment is refused, and the invoice turns Paid once it is covered.
    The invoice row is locked, so two payments can't both fit into the same outstanding amount."""
    invoice = get_invoice(db, body.invoice_id, for_update=True)
    _ensure_can_take(invoice, body)
    payment = Payment(
        **body.model_dump(),
        bank_ref=bank_ref,
        gateway_payment_id=gateway_payment_id,
        recorded_by_id=user.id if user else None,
    )
    db.add(payment)
    invoice.amount_paid += body.amount
    if invoice.amount_paid >= invoice.total:
        invoice.status = InvoiceStatus.PAID
    db.flush()
    return payment


def _ensure_can_take(invoice: Invoice, payment: PaymentIn) -> None:
    if invoice.status != InvoiceStatus.CONFIRMED:
        raise Conflict(_NOT_PAYABLE[invoice.status])
    outstanding = invoice.total - invoice.amount_paid
    if payment.amount > outstanding:
        raise Conflict(f"Payment exceeds the outstanding amount of {outstanding}.")
