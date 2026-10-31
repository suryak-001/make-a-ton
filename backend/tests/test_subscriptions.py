from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.enums import SubscriptionStatus as S
from app.models import Subscription, SubscriptionEvent
from app.services import subscriptions as svc

TODAY = date.today()


def body(catalog, plan=None, *, lines=None, **over):
    base = {
        "customer_id": catalog.customer.id,
        "plan_id": (plan or catalog.monthly).id,
        "start_date": str(TODAY),
        "payment_term_days": 15,
        "lines": lines
        if lines is not None
        else [{"product_id": catalog.crm.id, "variant_id": catalog.odoo.id, "quantity": 2}],
    }
    return {**base, **over}


def make(client, login, catalog, plan=None, *, who="staff@t.test", **kw):
    login(who)
    r = client.post("/api/subscriptions", json=body(catalog, plan, **kw))
    assert r.status_code == 201, r.text
    return r.json()


def go(client, sub_id, to, **extra):
    return client.post(f"/api/subscriptions/{sub_id}/transition", json={"to": to, **extra})


def activate(client, sub_id):
    for to in ("QUOTATION", "CONFIRMED", "ACTIVE"):
        assert go(client, sub_id, to).status_code == 200


# ───────────────────────── creating ─────────────────────────


def test_create_prices_lines_on_the_server_with_variant_and_tax(client, users, catalog, login):
    sub = make(client, login, catalog)
    line = sub["lines"][0]
    assert sub["number"] == "SUB-00001" and sub["status"] == "DRAFT"
    assert line["variant_label"] == "Brand: Odoo"
    assert line["unit_price"] == "1560.00"  # 1000 + 560 for the Odoo brand
    assert (line["subtotal"], line["tax_amount"], line["amount"]) == ("3120.00", "561.60", "3681.60")
    assert [t["name"] for t in line["taxes"]] == ["GST 18%"]
    assert (sub["subtotal"], sub["tax_total"], sub["total"]) == ("3120.00", "561.60", "3681.60")
    assert sub["editable"] is True and sub["allowed_actions"] == ["QUOTATION", "CLOSED"]


def test_numbers_are_sequential_and_creation_is_recorded(client, users, catalog, login, db):
    first = make(client, login, catalog)
    second = make(client, login, catalog)
    assert (first["number"], second["number"]) == ("SUB-00001", "SUB-00002")
    ev = first["events"]
    assert len(ev) == 1 and ev[0]["from_status"] is None and ev[0]["to_status"] == "DRAFT"
    assert ev[0]["actor_name"] == "Staff"


def test_only_staff_and_admin_can_create(client, users, catalog, login):
    assert client.post("/api/subscriptions", json=body(catalog)).status_code == 401
    login("cust@t.test")
    assert client.post("/api/subscriptions", json=body(catalog)).status_code == 403
    login("admin@t.test")
    assert client.post("/api/subscriptions", json=body(catalog)).status_code == 201


def test_line_quantity_below_plan_minimum_is_rejected(client, users, catalog, login):
    login("staff@t.test")
    low = body(catalog, catalog.strict, lines=[{"product_id": catalog.crm.id, "quantity": 4}])
    r = client.post("/api/subscriptions", json=low)
    assert r.status_code == 422 and r.json()["detail"][0]["loc"] == ["body", "lines.0.quantity"]
    ok = body(catalog, catalog.strict, lines=[{"product_id": catalog.crm.id, "quantity": 5}])
    assert client.post("/api/subscriptions", json=ok).status_code == 201
    # the minimum applies to every line, not to the total
    mixed = body(
        catalog,
        catalog.strict,
        lines=[
            {"product_id": catalog.crm.id, "quantity": 9},
            {"product_id": catalog.other.id, "quantity": 1},
        ],
    )
    bad = client.post("/api/subscriptions", json=mixed)
    assert bad.status_code == 422 and bad.json()["detail"][0]["loc"] == ["body", "lines.1.quantity"]


def test_plan_outside_its_dates_cannot_be_picked(client, users, catalog, login):
    login("staff@t.test")
    r = client.post("/api/subscriptions", json=body(catalog, catalog.ended))
    assert r.status_code == 422 and r.json()["detail"][0]["loc"] == ["body", "plan_id"]


def test_line_validation(client, users, catalog, login, db):
    login("staff@t.test")
    other_variant = catalog.other.variants[0]
    wrong_variant = body(
        catalog, lines=[{"product_id": catalog.crm.id, "variant_id": other_variant.id, "quantity": 1}]
    )
    assert client.post("/api/subscriptions", json=wrong_variant).status_code == 422
    assert client.post("/api/subscriptions", json=body(catalog, lines=[])).status_code == 422
    assert (
        client.post(
            "/api/subscriptions", json=body(catalog, lines=[{"product_id": 999, "quantity": 1}])
        ).status_code
        == 422
    )
    catalog.other.active = False
    db.commit()
    inactive = body(catalog, lines=[{"product_id": catalog.other.id, "quantity": 1}])
    assert client.post("/api/subscriptions", json=inactive).status_code == 422
    assert client.post("/api/subscriptions", json=body(catalog, customer_id=999)).status_code == 422
    backwards = body(catalog, start_date="2026-05-01", expiry_date="2026-04-01")
    assert client.post("/api/subscriptions", json=backwards).status_code == 422


def test_editing_drafts_and_quotations_only(client, users, catalog, login):
    sub = make(client, login, catalog)
    new_lines = [{"product_id": catalog.crm.id, "quantity": 1}]
    edited = client.put(f"/api/subscriptions/{sub['id']}", json=body(catalog, lines=new_lines, notes="  hi "))
    assert edited.status_code == 200
    assert (len(edited.json()["lines"]), edited.json()["total"], edited.json()["notes"]) == (
        1,
        "1180.00",
        "hi",
    )
    go(client, sub["id"], "QUOTATION")
    assert client.put(f"/api/subscriptions/{sub['id']}", json=body(catalog)).status_code == 200
    go(client, sub["id"], "CONFIRMED")
    assert client.put(f"/api/subscriptions/{sub['id']}", json=body(catalog)).status_code == 409


def test_delete_only_drafts(client, users, catalog, login):
    draft = make(client, login, catalog)
    assert client.delete(f"/api/subscriptions/{draft['id']}").status_code == 204
    assert client.get(f"/api/subscriptions/{draft['id']}").status_code == 404
    other = make(client, login, catalog)
    go(client, other["id"], "QUOTATION")
    assert client.delete(f"/api/subscriptions/{other['id']}").status_code == 409


# ───────────────────────── the state machine ─────────────────────────


def test_every_state_in_the_flow_can_be_walked_through_with_history(client, users, catalog, login):
    sub = make(client, login, catalog)
    sid = sub["id"]
    for to in ("QUOTATION", "CONFIRMED", "ACTIVE", "PAUSED", "ACTIVE", "CLOSED"):
        r = go(client, sid, to, reason=f"to {to}")
        assert r.status_code == 200, (to, r.text)
        assert r.json()["status"] == to
    final = client.get(f"/api/subscriptions/{sid}").json()
    trail = [(e["from_status"], e["to_status"]) for e in final["events"]]
    assert trail == [
        (None, "DRAFT"),
        ("DRAFT", "QUOTATION"),
        ("QUOTATION", "CONFIRMED"),
        ("CONFIRMED", "ACTIVE"),
        ("ACTIVE", "PAUSED"),
        ("PAUSED", "ACTIVE"),
        ("ACTIVE", "CLOSED"),
    ]
    assert final["events"][-1]["reason"] == "to CLOSED" and final["events"][-1]["actor_name"] == "Staff"
    assert final["allowed_actions"] == []  # closed is final


def test_activation_sets_next_invoice_date_to_the_start_date(client, users, catalog, login):
    start = str(TODAY + timedelta(days=3))
    sub = make(client, login, catalog, start_date=start)
    assert sub["next_invoice_date"] is None
    activate(client, sub["id"])
    active = client.get(f"/api/subscriptions/{sub['id']}").json()
    assert active["next_invoice_date"] == start and active["payment_term_days"] == 15 and active["lines"]
    go(client, sub["id"], "CLOSED")
    assert client.get(f"/api/subscriptions/{sub['id']}").json()["next_invoice_date"] is None


def test_illegal_transitions_are_rejected_on_the_server(client, users, catalog, login):
    sub = make(client, login, catalog)
    sid = sub["id"]
    for to in ("CONFIRMED", "ACTIVE", "PAUSED"):  # can't skip ahead from DRAFT
        assert go(client, sid, to).status_code == 409, to
    assert go(client, sid, "DRAFT").status_code == 409  # not a move at all
    go(client, sid, "QUOTATION")
    assert go(client, sid, "PAUSED").status_code == 409  # PAUSED only from ACTIVE
    go(client, sid, "CLOSED")
    for to in S:
        assert go(client, sid, to.value).status_code == 409, to  # closed is final
    assert client.get("/api/subscriptions/99999").status_code == 404
    assert go(client, 99999, "QUOTATION").status_code == 404


def test_plan_flags_gate_pause_and_early_close(client, users, catalog, login):
    sub = make(client, login, catalog, catalog.strict, lines=[{"product_id": catalog.crm.id, "quantity": 5}])
    sid = sub["id"]
    activate(client, sid)
    detail = client.get(f"/api/subscriptions/{sid}").json()
    assert detail["allowed_actions"] == []  # not pausable, not closable, not renewable
    assert go(client, sid, "PAUSED").status_code == 409
    assert go(client, sid, "CLOSED").status_code == 409
    assert client.post(f"/api/subscriptions/{sid}/renew", json={}).status_code == 409


def test_a_non_closable_plan_can_be_closed_once_it_has_ended(client, users, catalog, login, db):
    sub = make(client, login, catalog, catalog.strict, lines=[{"product_id": catalog.crm.id, "quantity": 5}])
    activate(client, sub["id"])
    row = db.get(Subscription, sub["id"])
    row.expiry_date = TODAY - timedelta(days=1)
    db.commit()
    assert go(client, sub["id"], "CLOSED").status_code == 200


def test_cannot_pause_while_billing_is_behind_and_resume_skips_the_paused_periods(
    client, users, catalog, login, db
):
    sub = make(client, login, catalog, start_date=str(TODAY - timedelta(days=45)))
    activate(client, sub["id"])  # next_invoice_date = start, 45 days ago: billing is behind
    blocked = go(client, sub["id"], "PAUSED")
    assert blocked.status_code == 409 and "Billing is behind" in blocked.json()["detail"]
    assert "PAUSED" not in client.get(f"/api/subscriptions/{sub['id']}").json()["allowed_actions"]

    # billing catches up to the next period, then the customer pauses
    row = db.get(Subscription, sub["id"])
    start = row.start_date
    row.next_invoice_date = svc.add_period(start, row.plan.billing_period, 2)  # in the future
    db.commit()
    assert go(client, sub["id"], "PAUSED").status_code == 200

    # resume after the pause ran past that date: periods inside the pause are skipped, never billed
    later = svc.add_period(start, row.plan.billing_period, 5) + timedelta(days=3)
    svc.transition_subscription(db, sub["id"], S.ACTIVE, today=later)
    db.commit()
    resumed = db.get(Subscription, sub["id"])
    assert resumed.next_invoice_date == svc.add_period(start, row.plan.billing_period, 6)
    assert resumed.next_invoice_date >= later  # nothing in the past is left to be billed


def test_quote_validity_counts_from_the_day_it_is_sent(client, users, catalog, login, db):
    sub = make(client, login, catalog, validity_days=10)
    assert sub["validity_days"] == 10
    sent_on = date(2026, 3, 1)
    svc.transition_subscription(db, sub["id"], S.QUOTATION, today=sent_on)
    db.commit()
    assert db.get(Subscription, sub["id"]).quotation_valid_until == date(2026, 3, 11)  # sent date + 10 days


def test_an_expired_quotation_cannot_be_confirmed(client, users, catalog, login, db):
    sub = make(client, login, catalog)
    go(client, sub["id"], "QUOTATION")
    row = db.get(Subscription, sub["id"])
    row.quotation_valid_until = TODAY - timedelta(days=1)
    db.commit()
    r = go(client, sub["id"], "CONFIRMED")
    assert r.status_code == 409 and "expired" in r.json()["detail"]
    assert "CONFIRMED" not in client.get(f"/api/subscriptions/{sub['id']}").json()["allowed_actions"]


# ───────────────────────── renewal ─────────────────────────


def test_renew_extends_the_expiry_by_one_plan_period_and_is_recorded(client, users, catalog, login):
    sub = make(client, login, catalog, expiry_date="2026-12-31")
    activate(client, sub["id"])
    assert "RENEW" in client.get(f"/api/subscriptions/{sub['id']}").json()["allowed_actions"]
    r = client.post(f"/api/subscriptions/{sub['id']}/renew", json={})
    assert r.status_code == 200 and r.json()["expiry_date"] == "2027-01-31"
    last = r.json()["events"][-1]
    assert last["from_status"] == last["to_status"] == "ACTIVE" and "Renewed" in last["reason"]


def test_renew_needs_an_expiry_date_and_a_live_subscription(client, users, catalog, login):
    open_ended = make(client, login, catalog)  # no expiry date
    activate(client, open_ended["id"])
    assert client.post(f"/api/subscriptions/{open_ended['id']}/renew", json={}).status_code == 409
    draft = make(client, login, catalog, expiry_date="2026-12-31")
    assert client.post(f"/api/subscriptions/{draft['id']}/renew", json={}).status_code == 409


# ───────────────────────── list ─────────────────────────


def test_list_filters_paginates_and_totals(client, users, catalog, login):
    a = make(client, login, catalog)
    b = make(client, login, catalog, catalog.strict, lines=[{"product_id": catalog.crm.id, "quantity": 5}])
    go(client, a["id"], "QUOTATION")
    everything = client.get("/api/subscriptions").json()
    assert everything["total"] == 2 and everything["items"][0]["number"] == b["number"]  # newest first
    assert everything["items"][1]["total"] == "3681.60"
    assert client.get("/api/subscriptions?status=QUOTATION").json()["total"] == 1
    assert client.get(f"/api/subscriptions?plan_id={catalog.strict.id}").json()["items"][0]["id"] == b["id"]
    assert client.get(f"/api/subscriptions?customer_id={catalog.customer.id}").json()["total"] == 2
    assert client.get("/api/subscriptions?customer_id=99999").json()["total"] == 0
    assert client.get("/api/subscriptions?q=SUB-00001").json()["total"] == 1
    assert client.get("/api/subscriptions?q=cust co").json()["total"] == 2
    page = client.get("/api/subscriptions?page=2&page_size=1").json()
    assert (page["total"], len(page["items"]), page["items"][0]["id"]) == (2, 1, a["id"])
    login("cust@t.test")
    assert client.get("/api/subscriptions").status_code == 403


# ───────────────────────── lifecycle job ─────────────────────────


def test_lifecycle_closes_ended_auto_close_subscriptions_and_expires_stale_quotes(
    client, users, catalog, login, db
):
    strict = make(
        client, login, catalog, catalog.strict, lines=[{"product_id": catalog.crm.id, "quantity": 5}]
    )
    activate(client, strict["id"])
    monthly = make(client, login, catalog)  # plan without auto_close
    activate(client, monthly["id"])
    still_valid = make(client, login, catalog)
    go(client, still_valid["id"], "QUOTATION")
    stale = make(client, login, catalog)
    go(client, stale["id"], "QUOTATION")
    for sid, field, value in [
        (strict["id"], "expiry_date", TODAY - timedelta(days=1)),
        (monthly["id"], "expiry_date", TODAY - timedelta(days=1)),
        (stale["id"], "quotation_valid_until", TODAY - timedelta(days=1)),
    ]:
        setattr(db.get(Subscription, sid), field, value)
    db.commit()

    login("staff@t.test")
    assert client.post("/api/subscriptions/run-lifecycle").status_code == 403  # admin only
    login("admin@t.test")
    r = client.post("/api/subscriptions/run-lifecycle")
    assert r.status_code == 200 and r.json() == {"closed": 1, "expired_quotations": 1}

    status = lambda sid: db.get(Subscription, sid).status  # noqa: E731
    db.expire_all()
    assert status(strict["id"]) == S.CLOSED  # ended + auto_close
    assert status(monthly["id"]) == S.ACTIVE  # ended but the plan doesn't auto-close
    assert status(stale["id"]) == S.CLOSED
    assert status(still_valid["id"]) == S.QUOTATION
    events = db.scalars(
        select(SubscriptionEvent).where(SubscriptionEvent.subscription_id == strict["id"])
    ).all()
    assert events[-1].reason == "Plan ended" and events[-1].actor_id is None  # done by the system

    assert client.post("/api/subscriptions/run-lifecycle").json() == {
        "closed": 0,
        "expired_quotations": 0,
    }  # idempotent


def test_money_is_decimal_exact(client, users, catalog, login, db):
    sub = make(
        client,
        login,
        catalog,
        lines=[{"product_id": catalog.crm.id, "variant_id": catalog.odoo.id, "quantity": 3}],
    )
    assert Decimal(sub["total"]) == Decimal("1560.00") * 3 * Decimal("1.18")
