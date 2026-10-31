"""A demo payment gateway, built in so customers can pay an invoice online without a real gateway account.

It follows the flow Indian payment gateways use, so a real one can replace it without touching the rest:
  1. The app creates an order for the invoice's balance. The amount is fixed here, never taken from the browser.
  2. The checkout collects a card (then a bank OTP), a UPI id or a netbanking bank, and the gateway charges it.
  3. The gateway returns a payment id and a signature: HMAC-SHA256 of "order_id|payment_id" with a secret only
     the server knows. The app checks the signature before it trusts the result.
  4. The gateway also tells the app directly when a payment succeeds, as a webhook would, so a customer who
     closes the tab straight after paying still has their invoice marked paid.
Recording is idempotent on the payment id (Payment.gateway_payment_id is unique), so steps 3 and 4 both
landing records the payment once.

Only published test instruments are accepted. No real card is ever charged, and card numbers are never stored:
a payment keeps the card's network and last four digits.
"""

import hashlib
import hmac
import re
import secrets
import string
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import Conflict, DomainError, Invalid, NotFound
from app.enums import GatewayOrderStatus, InvoiceStatus, PaymentMethod
from app.models import GatewayOrder, Invoice, Payment, User
from app.schemas.gateway import ChargeIn, ChargeOut
from app.schemas.money import PaymentIn
from app.services.payments import record_payment

MERCHANT = "Brightloop Software"
CURRENCY = "INR"
TEST_OTP = "123456"

# Test cards: number -> (network, why the bank declines it, or None to approve).
TEST_CARDS = {
    "4111111111111111": ("Visa", None),
    "5555555555554444": ("Mastercard", None),
    "4000000000000002": ("Visa", "Card declined by the issuing bank."),
    "4000000000009995": ("Visa", "Insufficient funds on the card."),
}
TEST_UPI = {"success@demo": None, "failure@demo": "The payment was declined in the UPI app."}
BANKS = {
    "HDFC": "HDFC Bank",
    "ICICI": "ICICI Bank",
    "SBI": "State Bank of India",
    "AXIS": "Axis Bank",
    "KOTAK": "Kotak Mahindra Bank",
}

_KEY = hashlib.sha256(f"demo-gateway:{settings.session_secret}".encode()).digest()
_ALPHABET = string.ascii_letters + string.digits


class PaymentDeclined(DomainError):
    """The gateway refused this attempt. The order stays open, so the customer can try again."""

    status_code = 402


def _new_id(prefix: str) -> str:
    return prefix + "".join(secrets.choice(_ALPHABET) for _ in range(14))


def sign(order_id: str, payment_id: str) -> str:
    return hmac.new(_KEY, f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()


# ───────────────────────────── 1. the order ─────────────────────────────


def create_order(db: Session, invoice: Invoice) -> GatewayOrder:
    """An order for everything still owed on a confirmed invoice."""
    if invoice.status != InvoiceStatus.CONFIRMED:
        raise Conflict("Only a confirmed invoice with a balance can be paid online.")
    balance = invoice.total - invoice.amount_paid
    if balance <= 0:
        raise Conflict("This invoice is already paid in full.")
    order = GatewayOrder(id=_new_id("order_"), invoice_id=invoice.id, amount=balance)
    db.add(order)
    db.flush()
    return order


# ───────────────────────────── 2. the charge (the gateway's side) ─────────────────────────────


@dataclass
class _Instrument:
    method: PaymentMethod
    label: str  # "Visa •••• 1111"
    decline: str | None


def _luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch) * (2 if i % 2 else 1)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


def _card(body: ChargeIn, today: date) -> _Instrument:
    if body.card is None:
        raise Invalid("Enter the card details.", field="card")
    digits = re.sub(r"\D", "", body.card.number)
    if not _luhn_ok(digits):
        raise Invalid("That card number isn't valid.", field="card.number")
    if digits not in TEST_CARDS:
        raise Invalid("This is a demo checkout. Use one of the test cards shown.", field="card.number")
    month, year = (int(x) for x in body.card.expiry.replace(" ", "").split("/"))
    if not 1 <= month <= 12:
        raise Invalid("The expiry month must be 01 to 12.", field="card.expiry")
    if (2000 + year, month) < (today.year, today.month):
        raise Invalid("This card has expired.", field="card.expiry")
    network, decline = TEST_CARDS[digits]
    if decline is None and body.otp != TEST_OTP:
        decline = "Incorrect OTP. The bank didn't authorise the payment."
    return _Instrument(PaymentMethod.CARD, f"{network} •••• {digits[-4:]}", decline)


def _upi(body: ChargeIn) -> _Instrument:
    vpa = (body.vpa or "").strip().lower()
    if not re.fullmatch(r"[\w.\-]{2,}@[a-z]{2,}", vpa):
        raise Invalid("Enter a UPI id like name@bank.", field="vpa")
    if vpa not in TEST_UPI:
        raise Invalid("This is a demo checkout. Use success@demo or failure@demo.", field="vpa")
    return _Instrument(PaymentMethod.UPI, vpa, TEST_UPI[vpa])


def _netbanking(body: ChargeIn) -> _Instrument:
    if body.bank is None or body.bank_outcome is None:
        raise Invalid("Choose your bank.", field="bank")
    decline = "The bank reported the payment as failed." if body.bank_outcome == "failure" else None
    return _Instrument(PaymentMethod.BANK_TRANSFER, BANKS[body.bank], decline)


def charge(db: Session, user: User, order_id: str, body: ChargeIn, today: date | None = None) -> ChargeOut:
    """Takes one payment attempt on an order. Approved: the order is paid and the app is told at once. Declined:
    PaymentDeclined, with the attempt counted, and the order stays open. Charging a paid order again returns the
    same payment instead of taking the money twice."""
    order = _own_order(db, user, order_id)
    if order.status != GatewayOrderStatus.CREATED:
        return _charged(order)
    instrument = {
        "card": lambda: _card(body, today or date.today()),
        "upi": lambda: _upi(body),
        "netbanking": lambda: _netbanking(body),
    }[body.method]()
    order.attempts += 1
    if instrument.decline:
        order.failure_reason = instrument.decline
        db.flush()
        raise PaymentDeclined(instrument.decline)
    order.status = GatewayOrderStatus.PAID
    order.payment_id = _new_id("pay_")
    order.method, order.instrument = instrument.method, instrument.label
    order.failure_reason = None
    order.paid_at = datetime.now(UTC)
    db.flush()
    settle(db, order)  # the gateway's server-to-server notification
    return _charged(order)


def _charged(order: GatewayOrder) -> ChargeOut:
    return ChargeOut(
        order_id=order.id,
        payment_id=order.payment_id,
        signature=sign(order.id, order.payment_id),
        method=order.method,
        instrument=order.instrument,
    )


def _own_order(db: Session, user: User, order_id: str) -> GatewayOrder:
    order = db.scalar(select(GatewayOrder).where(GatewayOrder.id == order_id).with_for_update())
    customer_id = user.customer.id if user.customer else None
    if order is None or customer_id is None or order.invoice.customer_id != customer_id:
        raise NotFound("Order not found.")
    return order


# ───────────────────────────── 3 and 4. the app records it ─────────────────────────────


def settle(db: Session, order: GatewayOrder) -> Payment | None:
    """Records a paid order as a payment on its invoice, once. If the invoice was settled some other way in the
    meantime, the money can't be applied: the order is marked for a refund instead."""
    existing = db.scalar(select(Payment).where(Payment.gateway_payment_id == order.payment_id))
    if existing is not None or order.status != GatewayOrderStatus.PAID:
        return existing
    body = PaymentIn(
        invoice_id=order.invoice_id,
        method=order.method,
        amount=order.amount,
        payment_date=order.paid_at.date() if order.paid_at else date.today(),
        note=f"Paid online · {order.instrument} · {order.payment_id}",
    )
    try:
        with db.begin_nested():
            return record_payment(db, body, None, gateway_payment_id=order.payment_id)
    except Conflict as e:
        order.status = GatewayOrderStatus.REFUND_DUE
        order.failure_reason = e.message
        db.flush()
        return None


def verify(
    db: Session, user: User, invoice_id: int, order_id: str, payment_id: str, signature: str
) -> Payment:
    """What the app does with the checkout's result: check the signature, then record the payment (once)."""
    order = _own_order(db, user, order_id)
    if order.invoice_id != invoice_id or order.payment_id != payment_id:
        raise Conflict("That payment doesn't belong to this invoice.")
    if not hmac.compare_digest(sign(order_id, payment_id), signature):
        raise Conflict("The payment signature doesn't match. Nothing was recorded.")
    payment = settle(db, order)
    if payment is None:
        raise Conflict(
            f"{order.failure_reason} The {order.amount} you paid will be refunded."
            if order.status == GatewayOrderStatus.REFUND_DUE
            else "This payment hasn't gone through."
        )
    return payment
