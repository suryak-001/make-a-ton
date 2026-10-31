from datetime import date, timedelta

from app.core.security import hash_password
from app.enums import Role
from app.models import Customer, Subscription, User

TODAY = date.today()


def staff_make(client, login, catalog, plan=None, *, status="ACTIVE", customer=None, **over):
    """Create a subscription as staff and move it to `status` along the allowed path."""
    login("staff@t.test")
    lines = over.pop("lines", [{"product_id": catalog.crm.id, "quantity": 5}])
    payload = {
        "customer_id": (customer or catalog.customer).id,
        "plan_id": (plan or catalog.monthly).id,
        "start_date": str(TODAY + timedelta(days=5)),  # in the future: nothing is overdue for billing
        "expiry_date": "2027-06-30",
        "lines": lines,
        **over,
    }
    sub = client.post("/api/subscriptions", json=payload).json()
    path = ["QUOTATION", "CONFIRMED", "ACTIVE"]
    for to in path[: path.index(status) + 1] if status in path else []:
        client.post(f"/api/subscriptions/{sub['id']}/transition", json={"to": to})
    return sub


def portal(client, login, who="cust@t.test"):
    assert login(who).status_code == 200


def act(client, sid, to, **kw):
    return client.post(f"/api/portal-subscriptions/{sid}/transition", json={"to": to, **kw})


def strict_lines(catalog):
    return [{"product_id": catalog.crm.id, "quantity": 5}]


def test_portal_requires_a_customer_login(client, users, catalog, login):
    assert client.get("/api/portal-subscriptions").status_code == 401
    login("staff@t.test")
    assert client.get("/api/portal-subscriptions").status_code == 403
    login("admin@t.test")
    assert client.get("/api/portal-subscriptions").status_code == 403


def test_customer_sees_only_their_own_non_draft_subscriptions(client, users, catalog, login, db):
    mine = staff_make(client, login, catalog)
    draft = staff_make(client, login, catalog, status="DRAFT")
    rival = Customer(name="Rival", email="rival@x.test")
    db.add(rival)
    db.commit()
    theirs = staff_make(client, login, catalog, customer=rival)

    portal(client, login)
    listing = client.get("/api/portal-subscriptions").json()
    assert [s["id"] for s in listing["items"]] == [mine["id"]] and listing["total"] == 1
    assert client.get(f"/api/portal-subscriptions/{mine['id']}").status_code == 200
    # someone else's record, and an internal draft of their own, are both 404 (never 403)
    assert client.get(f"/api/portal-subscriptions/{theirs['id']}").status_code == 404
    assert client.get(f"/api/portal-subscriptions/{draft['id']}").status_code == 404
    assert client.get("/api/portal-subscriptions/99999").status_code == 404


def test_customer_cannot_act_on_someone_elses_subscription(client, users, catalog, login, db):
    rival = Customer(name="Rival", email="rival@x.test")
    db.add(rival)
    db.commit()
    theirs = staff_make(client, login, catalog, customer=rival)
    portal(client, login)
    assert act(client, theirs["id"], "PAUSED").status_code == 404
    assert client.post(f"/api/portal-subscriptions/{theirs['id']}/renew", json={}).status_code == 404
    db.expire_all()
    assert db.get(Subscription, theirs["id"]).status.value == "ACTIVE"  # untouched


def test_portal_detail_hides_internal_fields(client, users, catalog, login):
    sub = staff_make(client, login, catalog, notes="internal: big discount promised")
    portal(client, login)
    detail = client.get(f"/api/portal-subscriptions/{sub['id']}").json()
    assert "notes" not in detail and "created_by" not in detail and "validity_days" not in detail
    assert all(e["actor_name"] is None for e in detail["events"])
    assert detail["lines"][0]["product_name"] == "CRM" and detail["plan"]["name"] == "Monthly"


def test_self_service_pause_resume_and_close_on_a_plan_that_allows_it(client, users, catalog, login):
    sub = staff_make(client, login, catalog)
    portal(client, login)
    sid = sub["id"]
    detail = client.get(f"/api/portal-subscriptions/{sid}").json()
    assert detail["allowed_actions"] == ["PAUSED", "CLOSED", "RENEW"]
    paused = act(client, sid, "PAUSED", reason="holiday")
    assert paused.status_code == 200 and paused.json()["status"] == "PAUSED"
    assert paused.json()["allowed_actions"] == ["ACTIVE", "CLOSED", "RENEW"]
    assert act(client, sid, "ACTIVE").json()["status"] == "ACTIVE"
    closed = act(client, sid, "CLOSED", reason="switching provider")
    assert closed.json()["status"] == "CLOSED" and closed.json()["allowed_actions"] == []
    reasons = [e["reason"] for e in closed.json()["events"]]
    assert "holiday" in reasons and "switching provider" in reasons

    login("staff@t.test")  # staff see who did it
    events = client.get(f"/api/subscriptions/{sid}").json()["events"]
    assert events[-1]["actor_name"] == "Cust"


def test_a_plan_that_cannot_be_paused_offers_no_pause_and_the_api_rejects_it(client, users, catalog, login):
    sub = staff_make(client, login, catalog, catalog.strict, lines=strict_lines(catalog))
    portal(client, login)
    detail = client.get(f"/api/portal-subscriptions/{sub['id']}").json()
    assert detail["allowed_actions"] == []  # no Pause, no Close, no Renew
    for to in ("PAUSED", "CLOSED"):
        r = act(client, sub["id"], to)
        assert r.status_code == 409, to
    assert client.post(f"/api/portal-subscriptions/{sub['id']}/renew", json={}).status_code == 409


def test_customers_can_only_pause_resume_and_close_never_staff_moves(client, users, catalog, login):
    sub = staff_make(client, login, catalog)
    portal(client, login)
    for to in ("QUOTATION", "CONFIRMED", "DRAFT"):
        assert act(client, sub["id"], to).status_code == 409, to
    quote = staff_make(client, login, catalog, status="QUOTATION")
    portal(client, login)
    assert act(client, quote["id"], "CONFIRMED").status_code == 409  # customers don't confirm quotes
    assert act(client, quote["id"], "CLOSED").status_code == 409  # only live subscriptions
    assert client.get(f"/api/portal-subscriptions/{quote['id']}").json()["allowed_actions"] == []


def test_self_service_renew(client, users, catalog, login):
    sub = staff_make(client, login, catalog)
    portal(client, login)
    r = client.post(f"/api/portal-subscriptions/{sub['id']}/renew", json={})
    assert r.status_code == 200 and r.json()["expiry_date"] == "2027-07-30"
    assert "Renewed" in r.json()["events"][-1]["reason"]


def test_portal_actions_cannot_be_used_by_staff(client, users, catalog, login):
    sub = staff_make(client, login, catalog)
    assert act(client, sub["id"], "PAUSED").status_code == 403
    assert client.post(f"/api/portal-subscriptions/{sub['id']}/renew", json={}).status_code == 403


def test_a_customer_login_without_a_customer_record_sees_nothing(client, users, catalog, login, db):
    db.add(
        User(
            email="orphan@t.test",
            name="Orphan",
            role=Role.CUSTOMER,
            password_hash=hash_password("Passw0rd!x"),
        )
    )
    db.commit()
    sub = staff_make(client, login, catalog)
    portal(client, login, "orphan@t.test")
    assert client.get("/api/portal-subscriptions").json() == {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 20,
    }
    assert client.get(f"/api/portal-subscriptions/{sub['id']}").status_code == 404
    assert act(client, sub["id"], "PAUSED").status_code == 404
