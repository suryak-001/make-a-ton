from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.enums import InvoiceStatus, SubscriptionStatus
from app.models import Customer, Invoice, Subscription, SubscriptionLine
from app.services.billing import generate_invoice_for_period, run_billing


def active_subscription(db, catalog, users, *, start=date(2026, 1, 31), next_date=None):
    sub = Subscription(
        number="SUB-MONEY-1",
        customer_id=catalog.customer.id,
        plan_id=catalog.monthly.id,
        status=SubscriptionStatus.ACTIVE,
        start_date=start,
        payment_term_days=15,
        next_invoice_date=next_date or start,
        created_by_id=users["admin"].id,
        lines=[
            SubscriptionLine(
                product_id=catalog.crm.id,
                variant_id=catalog.odoo.id,
                quantity=2,
                unit_price=Decimal("1560"),
                amount=Decimal("3681.60"),
                taxes=[catalog.gst],
            )
        ],
    )
    db.add(sub)
    db.commit()
    return sub


def test_tax_crud_is_admin_only(client, login, users):
    login("staff@t.test")
    assert client.post("/api/taxes", json={"name": "VAT", "kind": "PERCENT", "rate": "5"}).status_code == 403
    login("admin@t.test")
    made = client.post("/api/taxes", json={"name": "VAT", "kind": "PERCENT", "rate": "5"})
    assert made.status_code == 201
    assert made.json()["active"] is True
    assert client.get("/api/taxes").json()["total"] == 1


def test_invoice_generation_is_idempotent_and_snapshots_lines(db, catalog, users):
    sub = active_subscription(db, catalog, users)
    first = generate_invoice_for_period(db, sub.id, sub.start_date)
    db.flush()
    second = generate_invoice_for_period(db, sub.id, sub.start_date)
    assert second.id == first.id
    assert first.number is None
    assert first.subtotal == Decimal("3120.00")
    assert first.tax_total == Decimal("561.60")
    assert first.total == Decimal("3681.60")
    assert first.lines[0].description == "CRM"
    assert first.lines[0].tax_rate == Decimal("18.00")


def test_billing_catches_up_from_original_month_end(db, catalog, users):
    sub = active_subscription(db, catalog, users)
    result = run_billing(db, date(2026, 3, 31))
    db.commit()
    starts = list(
        db.scalars(
            select(Invoice.period_start)
            .where(Invoice.subscription_id == sub.id)
            .order_by(Invoice.period_start)
        )
    )
    assert result.created == 3
    assert starts == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)]
    assert sub.next_invoice_date == date(2026, 4, 30)
    assert run_billing(db, date(2026, 3, 31)).created == 0


def test_confirm_payment_and_overpayment_guard(client, login, db, catalog, users):
    sub = active_subscription(db, catalog, users, start=date.today())
    invoice = generate_invoice_for_period(db, sub.id, date.today())
    db.commit()
    login("staff@t.test")
    confirmed = client.post(f"/api/invoices/{invoice.id}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["number"].startswith(f"INV-{date.today().year}-")
    half = Decimal(confirmed.json()["total"]) / 2
    first = client.post(
        "/api/payments",
        json={
            "invoice_id": invoice.id,
            "method": "UPI",
            "amount": str(half),
            "payment_date": str(date.today()),
        },
    )
    assert first.status_code == 201
    too_much = client.post(
        "/api/payments",
        json={
            "invoice_id": invoice.id,
            "method": "CARD",
            "amount": str(half + 1),
            "payment_date": str(date.today()),
        },
    )
    assert too_much.status_code == 409
    paid = client.post(
        "/api/payments",
        json={
            "invoice_id": invoice.id,
            "method": "CARD",
            "amount": str(half),
            "payment_date": str(date.today()),
        },
    )
    assert paid.status_code == 201
    assert db.get(Invoice, invoice.id).status == InvoiceStatus.PAID


def test_portal_invoice_is_scoped_to_customer(client, login, db, catalog, users):
    sub = active_subscription(db, catalog, users, start=date.today())
    invoice = generate_invoice_for_period(db, sub.id, date.today())
    invoice.status = InvoiceStatus.CONFIRMED
    invoice.number = "INV-TEST-1"
    other_customer = Customer(name="Other", email="other@t.test")
    db.add(other_customer)
    db.commit()
    login("cust@t.test")
    assert client.get("/api/portal-invoices").json()["total"] == 1
    invoice.customer_id = other_customer.id
    db.commit()
    assert client.get(f"/api/portal-invoices/{invoice.id}").status_code == 404


def test_reports_use_paid_and_outstanding_totals(client, login, db, catalog, users):
    sub = active_subscription(db, catalog, users, start=date.today() - timedelta(days=40))
    invoice = generate_invoice_for_period(db, sub.id, sub.start_date)
    invoice.status = InvoiceStatus.CONFIRMED
    invoice.number = "INV-TEST-2"
    invoice.due_date = date.today() - timedelta(days=1)
    db.commit()
    login("staff@t.test")
    summary = client.get("/api/reports/summary")
    assert summary.status_code == 200
    assert summary.json()["active_subscriptions"] == 1
    assert Decimal(summary.json()["outstanding"]) == invoice.total
    assert summary.json()["overdue_count"] == 1
    revenue = client.get("/api/reports/revenue-by-month")
    assert revenue.status_code == 200
    assert Decimal(revenue.json()[0]["invoiced"]) == invoice.total
