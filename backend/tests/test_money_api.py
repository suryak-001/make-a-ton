"""Discount rules, payments, invoice browsing and report filters through the HTTP API."""

from datetime import date, timedelta
from decimal import Decimal

from app.enums import DiscountScope, InvoiceStatus
from app.models import Discount, Invoice
from app.services.billing import generate_invoice_for_period
from tests.test_billing import YESTERDAY, make_discount, make_sub

TODAY = date.today()


def discount_body(catalog, **over):
    body = {
        "name": "Volume 10%",
        "kind": "PERCENT",
        "value": "10",
        "start_date": str(YESTERDAY),
        "scope": "PRODUCT",
        "product_ids": [catalog.crm.id],
    }
    return {**body, **over}


def field_errors(response) -> dict[str, str]:
    assert response.status_code == 422, response.text
    return {item["loc"][-1]: item["msg"] for item in response.json()["detail"]}


def confirmed_invoice(db, catalog, *, number="SUB-T-1", due_in_days=15, **sub_options) -> Invoice:
    sub = make_sub(db, catalog, number=number, start=sub_options.pop("start", TODAY), **sub_options)
    invoice = generate_invoice_for_period(db, sub.id, sub.start_date)
    invoice.status = InvoiceStatus.CONFIRMED
    invoice.number = f"INV-{number}"
    invoice.due_date = TODAY + timedelta(days=due_in_days)
    db.commit()
    return invoice


def pay(client, invoice, amount, **over):
    body = {"invoice_id": invoice.id, "method": "UPI", "amount": str(amount), "payment_date": str(TODAY)}
    return client.post("/api/payments", json={**body, **over})


# ───────────────────────────── discount rules ─────────────────────────────


def test_discounts_are_admin_only(client, users, catalog, login):
    login("staff@t.test")
    assert client.get("/api/discounts").status_code == 403
    assert client.post("/api/discounts", json=discount_body(catalog)).status_code == 403
    login("admin@t.test")
    assert client.post("/api/discounts", json=discount_body(catalog)).status_code == 201


def test_an_invalid_rule_is_refused_with_a_message_on_the_right_field(client, users, catalog, login):
    login("admin@t.test")

    def refused(**over):
        return field_errors(client.post("/api/discounts", json=discount_body(catalog, **over)))

    assert "end before" in refused(end_date=str(YESTERDAY - timedelta(days=1)))["end_date"]
    assert "100%" in refused(value="150")["value"]
    assert "product" in refused(product_ids=[])["product_ids"]
    assert "doesn't exist" in refused(product_ids=[9999])["product_ids"]
    assert "subscription" in refused(scope="SUBSCRIPTION", product_ids=[])["subscription_ids"]


def test_a_fixed_discount_may_exceed_100(client, users, catalog, login):
    login("admin@t.test")
    assert (
        client.post("/api/discounts", json=discount_body(catalog, kind="FIXED", value="500")).status_code
        == 201
    )


def test_update_and_delete_a_discount(client, users, catalog, login):
    login("admin@t.test")
    created = client.post("/api/discounts", json=discount_body(catalog)).json()
    url = f"/api/discounts/{created['id']}"
    updated = client.put(url, json=discount_body(catalog, name="Renamed", usage_limit=3))
    assert updated.status_code == 200 and updated.json()["name"] == "Renamed"
    assert client.get(url).json()["usage_limit"] == 3
    assert client.delete(url).status_code == 204
    assert client.get(url).status_code == 404


def test_a_discount_cannot_be_limited_below_the_times_it_was_used(client, users, catalog, login, db):
    discount = make_discount(db, DiscountScope.PRODUCT, product=catalog.crm, usage_limit=5, used_count=3)
    login("admin@t.test")
    response = client.put(f"/api/discounts/{discount.id}", json=discount_body(catalog, usage_limit=2))
    assert "already been used 3 times" in field_errors(response)["usage_limit"]
    assert (
        client.put(f"/api/discounts/{discount.id}", json=discount_body(catalog, usage_limit=3)).status_code
        == 200
    )


def test_a_discount_that_is_on_an_invoice_cannot_be_deleted(client, users, catalog, login, db):
    sub = make_sub(db, catalog, start=TODAY)
    discount = make_discount(db, DiscountScope.PRODUCT, product=catalog.crm)
    generate_invoice_for_period(db, sub.id, TODAY)
    db.commit()
    login("admin@t.test")
    assert client.delete(f"/api/discounts/{discount.id}").status_code == 409
    assert db.get(Discount, discount.id) is not None


# ───────────────────────────── payments ─────────────────────────────


def test_partial_then_full_payment_marks_the_invoice_paid(client, users, catalog, db, login):
    invoice = confirmed_invoice(db, catalog)
    login("staff@t.test")
    half = invoice.total / 2
    assert pay(client, invoice, half).status_code == 201
    assert client.get(f"/api/invoices/{invoice.id}").json()["outstanding"] == str(invoice.total - half)
    assert pay(client, invoice, invoice.total - half).status_code == 201
    assert client.get(f"/api/invoices/{invoice.id}").json()["status"] == "PAID"


def test_payments_are_refused_with_a_clear_reason(client, users, catalog, db, login):
    draft = generate_invoice_for_period(db, make_sub(db, catalog, start=TODAY).id, TODAY)
    db.commit()
    login("staff@t.test")
    assert "Confirm the invoice" in pay(client, draft, 10).json()["detail"]

    paid = confirmed_invoice(db, catalog, number="SUB-T-2")
    login("staff@t.test")
    assert pay(client, paid, paid.total).status_code == 201
    assert "already paid" in pay(client, paid, 1).json()["detail"]

    open_invoice = confirmed_invoice(db, catalog, number="SUB-T-3")
    login("staff@t.test")
    assert "exceeds the outstanding" in pay(client, open_invoice, open_invoice.total + 1).json()["detail"]


def test_a_payment_date_in_the_future_is_refused_on_that_field(client, users, catalog, db, login):
    invoice = confirmed_invoice(db, catalog)
    login("staff@t.test")
    tomorrow = TODAY + timedelta(days=1)
    assert "future" in field_errors(pay(client, invoice, 10, payment_date=str(tomorrow)))["payment_date"]
    assert field_errors(pay(client, invoice, 0))["amount"]


def test_payments_can_be_filtered_by_method_and_date(client, users, catalog, db, login):
    invoice = confirmed_invoice(db, catalog)
    login("staff@t.test")
    pay(client, invoice, 10, method="CASH")
    pay(client, invoice, 20, method="UPI", payment_date=str(TODAY - timedelta(days=5)))
    assert client.get("/api/payments").json()["total"] == 2
    assert client.get("/api/payments?method=CASH").json()["total"] == 1
    assert client.get(f"/api/payments?from_date={TODAY}").json()["total"] == 1


# ───────────────────────────── invoices ─────────────────────────────


def test_invoices_filter_by_customer_dates_status_and_overdue(client, users, catalog, db, login):
    confirmed_invoice(db, catalog, number="SUB-T-1", due_in_days=-3)  # overdue
    confirmed_invoice(db, catalog, number="SUB-T-2", due_in_days=10)
    login("staff@t.test")
    assert client.get("/api/invoices").json()["total"] == 2
    assert client.get("/api/invoices?overdue=true").json()["total"] == 1
    assert client.get("/api/invoices?status=PAID").json()["total"] == 0
    assert client.get(f"/api/invoices?customer_id={catalog.customer.id}").json()["total"] == 2
    assert client.get("/api/invoices?customer_id=9999").json()["total"] == 0
    assert client.get(f"/api/invoices?from_date={TODAY + timedelta(days=1)}").json()["total"] == 0


def test_the_print_page_escapes_what_it_prints(client, users, catalog, db, login):
    invoice = confirmed_invoice(db, catalog)
    invoice.lines[0].description = "<script>alert(1)</script>"
    db.commit()
    login("staff@t.test")
    html = client.get(f"/api/invoices/{invoice.id}/print").text
    assert "<script>alert" not in html and "&lt;script&gt;" in html


def test_the_print_page_shows_what_the_invoice_screen_shows(client, users, catalog, db, login):
    invoice = confirmed_invoice(db, catalog)
    login("staff@t.test")
    pay(client, invoice, 1000)
    html = client.get(f"/api/invoices/{invoice.id}/print").text
    assert "Confirmed" in html and invoice.due_date.strftime("%d %b %Y") in html
    assert "₹1,000.00" in html and "Outstanding" in html and str(invoice.period_start) not in html


def test_a_cancelled_or_paid_invoice_cannot_be_cancelled_again(client, users, catalog, db, login):
    invoice = confirmed_invoice(db, catalog)
    login("staff@t.test")
    assert client.post(f"/api/invoices/{invoice.id}/cancel").status_code == 200
    assert client.post(f"/api/invoices/{invoice.id}/cancel").status_code == 409
    assert client.post(f"/api/invoices/{invoice.id}/confirm").status_code == 409


# ───────────────────────────── reports ─────────────────────────────


def test_the_summary_adds_up_and_respects_the_filters(client, users, catalog, db, login):
    invoice = confirmed_invoice(db, catalog, due_in_days=-2)
    login("staff@t.test")
    pay(client, invoice, 1000)
    summary = client.get("/api/reports/summary").json()
    assert Decimal(summary["invoiced"]) == invoice.total
    assert Decimal(summary["collected"]) == Decimal("1000")
    assert Decimal(summary["outstanding"]) == invoice.total - 1000
    assert (summary["active_subscriptions"], summary["overdue_count"]) == (1, 1)

    other_plan = client.get(f"/api/reports/summary?plan_id={catalog.strict.id}").json()
    assert (other_plan["active_subscriptions"], other_plan["invoiced"], other_plan["overdue_count"]) == (
        0,
        "0.00",
        0,
    )
    mine = client.get(f"/api/reports/summary?customer_id={catalog.customer.id}&plan_id={catalog.monthly.id}")
    assert Decimal(mine.json()["invoiced"]) == invoice.total


def test_overdue_list_and_revenue_by_month_follow_the_filters(client, users, catalog, db, login):
    invoice = confirmed_invoice(db, catalog, due_in_days=-2)
    login("staff@t.test")
    pay(client, invoice, 500)
    assert [i["id"] for i in client.get("/api/reports/overdue").json()] == [invoice.id]
    assert client.get("/api/reports/overdue?customer_id=9999").json() == []
    month = client.get("/api/reports/revenue-by-month").json()[0]
    assert (Decimal(month["invoiced"]), Decimal(month["collected"])) == (invoice.total, Decimal("500"))
    assert client.get("/api/reports/revenue-by-month?plan_id=9999").json() == []


def test_an_invoice_tells_the_ui_which_actions_are_allowed(client, users, catalog, db, login):
    draft = generate_invoice_for_period(db, make_sub(db, catalog, start=TODAY).id, TODAY)
    db.commit()
    login("staff@t.test")

    def actions(invoice):
        return client.get(f"/api/invoices/{invoice.id}").json()["allowed_actions"]

    assert actions(draft) == ["confirm", "cancel"]
    open_invoice = confirmed_invoice(db, catalog, number="SUB-T-2")
    login("staff@t.test")
    assert actions(open_invoice) == ["pay", "send", "print", "cancel"]
    pay(client, open_invoice, 10)
    assert actions(open_invoice) == ["pay", "send", "print"]  # a part-paid invoice can no longer be cancelled
    assert client.post(f"/api/invoices/{open_invoice.id}/cancel").status_code == 409
