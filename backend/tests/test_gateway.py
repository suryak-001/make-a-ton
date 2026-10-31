"""Paying an invoice online through the demo gateway, from the customer portal."""

from datetime import date

from app.core.security import hash_password
from app.enums import GatewayOrderStatus, InvoiceStatus, Role
from app.models import Customer, GatewayOrder, Payment, User
from tests.test_money_api import confirmed_invoice, pay

GOOD_CARD = {"number": "4111 1111 1111 1111", "expiry": "12/30", "cvv": "123"}


def checkout(client, invoice):
    response = client.post(f"/api/portal-invoices/{invoice.id}/checkout")
    assert response.status_code == 200, response.text
    return response.json()


def charge(client, order, **body):
    body = {"method": "card", "card": GOOD_CARD, "otp": "123456", **body}
    return client.post(f"/api/demo-gateway/orders/{order['order_id']}/charge", json=body)


def verify(client, invoice, paid, **over):
    body = {k: paid[k] for k in ("order_id", "payment_id", "signature")} | over
    return client.post(f"/api/portal-invoices/{invoice.id}/checkout/verify", json=body)


def test_a_customer_pays_by_card_and_the_invoice_turns_paid(client, users, catalog, login, db):
    invoice = confirmed_invoice(db, catalog)
    login("cust@t.test")
    order = checkout(client, invoice)
    assert (
        order["amount"] == str(invoice.total)
        and order["test_mode"]
        and order["order_id"].startswith("order_")
    )

    paid = charge(client, order)
    assert paid.status_code == 200, paid.text
    assert paid.json()["instrument"] == "Visa •••• 1111" and paid.json()["payment_id"].startswith("pay_")

    result = verify(client, invoice, paid.json())
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "PAID" and result.json()["outstanding"] == "0.00"
    payment = db.query(Payment).one()
    assert payment.method == "CARD" and payment.recorded_by_id is None
    assert payment.note == f"Paid online · Visa •••• 1111 · {paid.json()['payment_id']}"
    assert "4111111111111111" not in payment.note  # the card number is never kept

    assert verify(client, invoice, paid.json()).status_code == 200  # verifying twice records once
    assert db.query(Payment).count() == 1


def test_the_payment_is_recorded_even_if_the_customer_never_comes_back(client, users, catalog, login, db):
    invoice = confirmed_invoice(db, catalog)
    login("cust@t.test")
    assert charge(client, checkout(client, invoice)).status_code == 200
    db.refresh(invoice)
    assert (
        invoice.status == InvoiceStatus.PAID
    )  # the gateway's notification settled it without the verify step


def test_a_forged_signature_is_refused(client, users, catalog, login, db):
    invoice = confirmed_invoice(db, catalog)
    login("cust@t.test")
    paid = charge(client, checkout(client, invoice)).json()
    response = verify(client, invoice, paid, signature="0" * 64)
    assert response.status_code == 409 and "signature" in response.json()["detail"]


def test_a_declined_attempt_can_be_retried_on_the_same_order(client, users, catalog, login, db):
    invoice = confirmed_invoice(db, catalog)
    login("cust@t.test")
    order = checkout(client, invoice)
    declined = charge(client, order, card={**GOOD_CARD, "number": "4000000000000002"})
    assert declined.status_code == 402 and "declined" in declined.json()["detail"]
    wrong_otp = charge(client, order, otp="000000")
    assert wrong_otp.status_code == 402 and "OTP" in wrong_otp.json()["detail"]
    stored = db.get(GatewayOrder, order["order_id"])
    db.refresh(stored)
    assert stored.attempts == 2 and stored.status == GatewayOrderStatus.CREATED
    db.refresh(invoice)
    assert invoice.status == InvoiceStatus.CONFIRMED and db.query(Payment).count() == 0

    assert charge(client, order).status_code == 200
    db.refresh(invoice)
    assert invoice.status == InvoiceStatus.PAID


def test_only_test_cards_are_accepted(client, users, catalog, login, db):
    invoice = confirmed_invoice(db, catalog)
    login("cust@t.test")
    order = checkout(client, invoice)
    real_looking = charge(client, order, card={**GOOD_CARD, "number": "4242 4242 4242 4242"})
    assert real_looking.status_code == 422 and "test cards" in real_looking.text
    assert (
        charge(client, order, card={**GOOD_CARD, "number": "4111111111111112"}).status_code == 422
    )  # bad Luhn
    expired = charge(client, order, card={**GOOD_CARD, "expiry": f"01/{date.today().year % 100 - 1:02d}"})
    assert expired.status_code == 422 and "expired" in expired.text


def test_upi_and_netbanking(client, users, catalog, login, db):
    first = confirmed_invoice(db, catalog, number="SUB-T-1")
    second = confirmed_invoice(db, catalog, number="SUB-T-2")
    login("cust@t.test")

    order = checkout(client, first)
    assert charge(client, order, method="upi", vpa="failure@demo").status_code == 402
    assert charge(client, order, method="upi", vpa="someone@okhdfc").status_code == 422
    upi = charge(client, order, method="upi", vpa="Success@Demo")
    assert upi.status_code == 200 and upi.json()["method"] == "UPI"

    order = checkout(client, second)
    assert charge(client, order, method="netbanking", bank="HDFC", bank_outcome="failure").status_code == 402
    bank = charge(client, order, method="netbanking", bank="HDFC", bank_outcome="success")
    assert bank.status_code == 200 and bank.json()["instrument"] == "HDFC Bank"
    assert {p.method for p in db.query(Payment)} == {"UPI", "BANK_TRANSFER"}


def test_charging_a_paid_order_again_takes_no_more_money(client, users, catalog, login, db):
    invoice = confirmed_invoice(db, catalog)
    login("cust@t.test")
    order = checkout(client, invoice)
    first, again = charge(client, order).json(), charge(client, order).json()
    assert first["payment_id"] == again["payment_id"]
    assert db.query(Payment).count() == 1
    assert (
        client.post(f"/api/portal-invoices/{invoice.id}/checkout").status_code == 409
    )  # nothing left to pay


def test_money_taken_after_the_invoice_was_settled_is_marked_for_refund(client, users, catalog, login, db):
    invoice = confirmed_invoice(db, catalog)
    login("cust@t.test")
    order = checkout(client, invoice)
    login("staff@t.test")
    assert pay(client, invoice, invoice.total).status_code == 201  # paid by bank transfer meanwhile
    login("cust@t.test")
    paid = charge(client, order)
    assert paid.status_code == 200
    response = verify(client, invoice, paid.json())
    assert response.status_code == 409 and "refunded" in response.json()["detail"]
    stored = db.get(GatewayOrder, order["order_id"])
    db.refresh(stored)
    assert stored.status == GatewayOrderStatus.REFUND_DUE and db.query(Payment).count() == 1


def test_only_the_invoice_owner_can_pay_it(client, users, catalog, login, db):
    invoice = confirmed_invoice(db, catalog)
    login("cust@t.test")
    order = checkout(client, invoice)

    rival = User(
        email="rival@t.test", name="Rival", role=Role.CUSTOMER, password_hash=hash_password("Passw0rd!x")
    )
    db.add(rival)
    db.flush()
    db.add(Customer(name="Rival Co", email="rival@t.test", user_id=rival.id))
    db.commit()
    login("rival@t.test")
    assert client.post(f"/api/portal-invoices/{invoice.id}/checkout").status_code == 404
    assert charge(client, order).status_code == 404
    login("staff@t.test")
    assert client.post(f"/api/portal-invoices/{invoice.id}/checkout").status_code == 403
