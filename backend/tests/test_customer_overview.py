"""The customer page and the CSV downloads."""

import csv
import io
from decimal import Decimal

from app.models import Customer
from tests.test_money_api import confirmed_invoice, pay
from tests.test_portal import staff_make


def rows(response) -> list[dict]:
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/csv")
    return list(csv.DictReader(io.StringIO(response.text.lstrip("﻿"))))


def test_overview_matches_the_dashboard_for_that_customer(client, users, catalog, login, db):
    invoice = confirmed_invoice(db, catalog)
    login("staff@t.test")
    assert pay(client, invoice, "1000.00").status_code == 201

    overview = client.get(f"/api/customers/{catalog.customer.id}/overview")
    assert overview.status_code == 200, overview.text
    body = overview.json()
    dashboard = client.get(f"/api/reports/summary?customer_id={catalog.customer.id}").json()
    assert body["summary"] == dashboard
    assert body["summary"]["outstanding"] == str(invoice.total - Decimal("1000.00"))
    assert body["average_days_late"] == "-15.0"  # paid today, due in 15 days
    assert [i["id"] for i in body["invoices"]] == [invoice.id]
    assert body["payments"][0]["amount"] == "1000.00"
    kinds = {item["kind"] for item in body["timeline"]}
    assert {"invoice", "payment"} <= kinds


def test_overview_timeline_includes_subscription_history(client, users, catalog, login, db):
    sub = staff_make(client, login, catalog)
    timeline = client.get(f"/api/customers/{catalog.customer.id}/overview").json()["timeline"]
    titles = [item["title"] for item in timeline]
    assert f"{sub['number']}: confirmed → active" in titles
    assert f"{sub['number']} created as a draft" in titles


def test_overview_is_for_staff_and_404s_for_unknown_customers(client, users, catalog, login):
    login("cust@t.test")
    assert client.get(f"/api/customers/{catalog.customer.id}/overview").status_code == 403
    login("staff@t.test")
    assert client.get("/api/customers/99999/overview").status_code == 404


def test_exports_follow_the_list_filters(client, users, catalog, login, db):
    paid = confirmed_invoice(db, catalog, number="SUB-T-1")
    confirmed_invoice(db, catalog, number="SUB-T-2")
    login("staff@t.test")
    pay(client, paid, paid.total)

    everything = rows(client.get("/api/invoices/export.csv"))
    assert len(everything) == 2 and everything[0]["Customer"] == "Cust Co"
    only_paid = rows(client.get("/api/invoices/export.csv?status=PAID"))
    assert [r["Invoice"] for r in only_paid] == ["INV-SUB-T-1"] and only_paid[0]["Outstanding"] == "0.00"

    payments = rows(client.get("/api/payments/export.csv"))
    assert payments[0]["Amount"] == str(paid.total) and payments[0]["Recorded by"] == "Staff"
    assert len(rows(client.get("/api/subscriptions/export.csv"))) == 2
    assert rows(client.get("/api/customers/export.csv?q=cust"))[0]["Portal login"] == "yes"


def test_exports_neutralise_spreadsheet_formulas(client, users, login, db):
    db.add(Customer(name='=HYPERLINK("http://x")', email="f@x.test"))
    db.commit()
    login("staff@t.test")
    assert rows(client.get("/api/customers/export.csv?q=HYPERLINK"))[0]["Name"].startswith("'=")


def test_exports_are_for_staff_only(client, users, login):
    login("cust@t.test")
    for path in ("invoices", "payments", "subscriptions", "customers"):
        assert client.get(f"/api/{path}/export.csv").status_code == 403


def test_invoice_search_matches_number_or_customer(client, users, catalog, login, db):
    confirmed_invoice(db, catalog, number="SUB-T-1")
    login("staff@t.test")
    assert client.get("/api/invoices?q=SUB-T-1").json()["total"] == 1
    assert client.get("/api/invoices?q=cust co").json()["total"] == 1
    assert client.get("/api/invoices?q=nobody").json()["total"] == 0
