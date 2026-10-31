"""The role dashboards: admin proof and aging, the staff queue, the customer's own home, and one reminder per stage."""

from datetime import date, timedelta

from sqlalchemy import func, select

from app.enums import SubscriptionStatus
from app.models import Customer, InvoiceReminder, Subscription
from tests.test_money_api import confirmed_invoice

TODAY = date.today()


def buckets(client):
    return {b["key"]: b for b in client.get("/api/dashboard/aging").json()}


def test_aging_sorts_open_invoices_into_buckets_and_ignores_paid_ones(client, users, catalog, login, db):
    confirmed_invoice(db, catalog, number="A", due_in_days=5)
    confirmed_invoice(db, catalog, number="B", due_in_days=-10, start=TODAY - timedelta(days=40))
    confirmed_invoice(db, catalog, number="C", due_in_days=-45, start=TODAY - timedelta(days=80))
    confirmed_invoice(db, catalog, number="D", due_in_days=-120, start=TODAY - timedelta(days=200))
    paid = confirmed_invoice(db, catalog, number="E", due_in_days=-10, start=TODAY - timedelta(days=60))
    paid.amount_paid = paid.total
    db.commit()
    login("admin@t.test")
    b = buckets(client)
    assert [b[k]["count"] for k in ("current", "1-30", "31-60", "61-90", "90+")] == [1, 1, 1, 0, 1]
    assert b["current"]["amount"] == "3681.60"


def test_proof_reports_counts_and_no_duplicate_billing(client, users, catalog, login, db):
    confirmed_invoice(db, catalog, number="A")
    login("admin@t.test")
    proof = client.get("/api/dashboard/proof").json()
    assert proof["invoices"] == 1 and proof["subscriptions"] == 1
    assert proof["duplicate_invoice_periods"] == 0
    assert proof["measured_ms"] >= 0


def test_setup_steps_follow_real_data(client, users, catalog, login, db):
    login("admin@t.test")
    done = {s["key"]: s["done"] for s in client.get("/api/dashboard/setup").json()}
    assert done["product"] and done["plan"] and not done["subscription"] and not done["billing"]
    confirmed_invoice(db, catalog, number="A")
    done = {s["key"]: s["done"] for s in client.get("/api/dashboard/setup").json()}
    assert done["subscription"] and done["billing"] and not done["payment"]


def test_admin_screens_refuse_staff_and_customers(client, users, catalog, login):
    for who in ("staff@t.test", "cust@t.test"):
        login(who)
        for path in ("aging", "proof", "setup"):
            assert client.get(f"/api/dashboard/{path}").status_code == 403
    login("staff@t.test")
    assert client.get("/api/dashboard/queue").status_code == 200
    login("cust@t.test")
    assert client.get("/api/dashboard/queue").status_code == 403


def test_the_staff_queue_lists_renewals_expiring_quotes_and_invoices_to_chase(
    client, users, catalog, login, db
):
    sub = confirmed_invoice(
        db, catalog, number="A", due_in_days=-3, start=TODAY - timedelta(days=20)
    ).subscription
    sub.expiry_date = TODAY + timedelta(days=5)
    db.commit()
    login("staff@t.test")
    queue = client.get("/api/dashboard/queue").json()
    assert [r["number"] for r in queue["renewals_due"]] == ["A"] and queue["renewals_due"][0][
        "days_left"
    ] == 5
    assert queue["overdue_invoices"] == 1
    chase = queue["to_chase"][0]
    assert chase["days_overdue"] == 3 and chase["stage"] == "1-30" and chase["reminded"] is False


def test_a_reminder_goes_out_once_per_invoice_per_stage(client, users, catalog, login, db):
    invoice = confirmed_invoice(db, catalog, number="A", due_in_days=-3, start=TODAY - timedelta(days=20))
    login("staff@t.test")
    first = client.post(f"/api/dashboard/remind/{invoice.id}")
    assert first.status_code == 200 and first.json() == {"stage": "1-30"}
    again = client.post(f"/api/dashboard/remind/{invoice.id}")
    assert again.status_code == 409
    assert db.scalar(select(func.count()).select_from(InvoiceReminder)) == 1
    assert client.get("/api/dashboard/queue").json()["to_chase"][0]["reminded"] is True
    # Moving to the next stage allows the next reminder.
    invoice.due_date = TODAY - timedelta(days=40)
    db.commit()
    assert client.post(f"/api/dashboard/remind/{invoice.id}").json() == {"stage": "31-60"}


def test_an_invoice_that_is_not_overdue_cannot_be_chased(client, users, catalog, login, db):
    invoice = confirmed_invoice(db, catalog, number="A", due_in_days=10)
    login("staff@t.test")
    assert client.post(f"/api/dashboard/remind/{invoice.id}").status_code == 422
    assert client.post("/api/dashboard/remind/999999").status_code == 404
    login("cust@t.test")
    assert client.post(f"/api/dashboard/remind/{invoice.id}").status_code == 403


def test_the_customer_home_shows_only_their_own_account(client, users, catalog, login, db):
    mine = confirmed_invoice(db, catalog, number="A", due_in_days=-4, start=TODAY - timedelta(days=20))
    mine.subscription.expiry_date = TODAY + timedelta(days=3)
    stranger = Customer(name="Other Co", email="other@t.test")
    db.add(stranger)
    db.flush()
    db.add(
        Subscription(
            number="SUB-X",
            customer_id=stranger.id,
            plan_id=catalog.monthly.id,
            status=SubscriptionStatus.ACTIVE,
            start_date=TODAY,
            next_invoice_date=TODAY,
        )
    )
    db.commit()
    login("cust@t.test")
    home = client.get("/api/dashboard/portal").json()
    assert [s["number"] for s in home["subscriptions"]] == ["A"]
    assert home["overdue_count"] == 1 and home["outstanding"] == home["overdue_amount"]
    kinds = [a["kind"] for a in home["alerts"]]
    assert kinds == ["danger", "warning"]
    assert home["next_due"]["id"] == mine.id


def test_a_customer_with_nothing_owed_sees_all_paid_up(client, users, catalog, login, db):
    invoice = confirmed_invoice(db, catalog, number="A", due_in_days=10)
    invoice.amount_paid = invoice.total
    db.commit()
    login("cust@t.test")
    home = client.get("/api/dashboard/portal").json()
    assert home["outstanding"] == "0.00" and [a["kind"] for a in home["alerts"]] == ["success"]
    login("staff@t.test")
    assert client.get("/api/dashboard/portal").status_code == 403
