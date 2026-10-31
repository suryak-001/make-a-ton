from datetime import date, timedelta

TODAY = date.today()


def template_body(catalog, **over):
    base = {
        "name": "Enterprise (Odoo)",
        "plan_id": catalog.monthly.id,
        "validity_days": 21,
        "notes": " standard offer ",
        "lines": [
            {"product_id": catalog.crm.id, "variant_id": catalog.odoo.id, "quantity": 10},
            {"product_id": catalog.other.id, "quantity": 1},
        ],
    }
    return {**base, **over}


def test_templates_are_managed_by_staff_and_admin_only(client, users, catalog, login):
    assert client.get("/api/quotation-templates").status_code == 401
    login("cust@t.test")
    assert client.get("/api/quotation-templates").status_code == 403
    assert client.post("/api/quotation-templates", json=template_body(catalog)).status_code == 403
    login("staff@t.test")
    r = client.post("/api/quotation-templates", json=template_body(catalog))
    assert r.status_code == 201
    t = r.json()
    assert (t["name"], t["validity_days"], t["notes"], t["plan"]["name"]) == (
        "Enterprise (Odoo)",
        21,
        "standard offer",
        "Monthly",
    )
    assert [(ln["product_name"], ln["variant_label"], ln["quantity"]) for ln in t["lines"]] == [
        ("CRM", "Brand: Odoo", 10),
        ("Other", None, 1),
    ]


def test_template_crud_roundtrip(client, users, catalog, login):
    login("admin@t.test")
    tid = client.post("/api/quotation-templates", json=template_body(catalog)).json()["id"]
    assert client.get("/api/quotation-templates").json()["total"] == 1
    assert client.get("/api/quotation-templates?q=odoo").json()["total"] == 1
    assert client.get("/api/quotation-templates?q=zzz").json()["total"] == 0
    changed = template_body(
        catalog, name="Renamed", validity_days=7, lines=[{"product_id": catalog.crm.id, "quantity": 2}]
    )
    out = client.put(f"/api/quotation-templates/{tid}", json=changed).json()
    assert (out["name"], out["validity_days"], len(out["lines"])) == ("Renamed", 7, 1)
    assert client.get(f"/api/quotation-templates/{tid}").json()["name"] == "Renamed"
    assert client.delete(f"/api/quotation-templates/{tid}").status_code == 204
    assert client.get(f"/api/quotation-templates/{tid}").status_code == 404


def test_template_validation(client, users, catalog, login):
    login("staff@t.test")
    post = lambda **kw: client.post("/api/quotation-templates", json=template_body(catalog, **kw))  # noqa: E731
    assert post(lines=[]).status_code == 422
    assert post(validity_days=0).status_code == 422
    assert post(plan_id=99999).status_code == 422
    assert post(name="  ").status_code == 422
    bad_variant = [{"product_id": catalog.crm.id, "variant_id": catalog.other.variants[0].id, "quantity": 1}]
    assert post(lines=bad_variant).status_code == 422
    too_few = post(plan_id=catalog.strict.id, lines=[{"product_id": catalog.crm.id, "quantity": 4}])
    assert too_few.status_code == 422 and too_few.json()["detail"][0]["loc"] == ["body", "lines.0.quantity"]


def test_create_subscription_from_template_copies_plan_and_lines(client, users, catalog, login):
    login("staff@t.test")
    tid = client.post("/api/quotation-templates", json=template_body(catalog)).json()["id"]
    r = client.post(
        f"/api/quotation-templates/{tid}/create-subscription", json={"customer_id": catalog.customer.id}
    )
    assert r.status_code == 201, r.text
    sub = r.json()
    assert (sub["status"], sub["plan"]["name"], sub["start_date"], sub["validity_days"]) == (
        "DRAFT",
        "Monthly",
        str(TODAY),
        21,
    )
    assert [(ln["product_name"], ln["quantity"], ln["unit_price"]) for ln in sub["lines"]] == [
        ("CRM", 10, "1560.00"),
        ("Other", 1, "50.00"),
    ]
    assert sub["quotation_valid_until"] == str(
        TODAY + timedelta(days=21)
    )  # provisional expiry shown on the quote
    assert sub["events"][0]["to_status"] == "DRAFT"


def test_sending_the_quote_restarts_the_validity_clock(client, users, catalog, login, db):
    from app.enums import SubscriptionStatus as S
    from app.models import Subscription
    from app.services import subscriptions as svc

    login("staff@t.test")
    tid = client.post("/api/quotation-templates", json=template_body(catalog)).json()["id"]
    sub = client.post(
        f"/api/quotation-templates/{tid}/create-subscription", json={"customer_id": catalog.customer.id}
    ).json()
    sent_on = date(2026, 6, 1)  # sent well after it was created
    svc.transition_subscription(db, sub["id"], S.QUOTATION, today=sent_on)
    db.commit()
    assert db.get(Subscription, sub["id"]).quotation_valid_until == sent_on + timedelta(days=21)


def test_from_template_respects_plan_and_customer_and_dates(client, users, catalog, login):
    login("staff@t.test")
    tid = client.post("/api/quotation-templates", json=template_body(catalog)).json()["id"]
    url = f"/api/quotation-templates/{tid}/create-subscription"
    assert client.post(url, json={"customer_id": 99999}).status_code == 422
    assert (
        client.post(
            url,
            json={
                "customer_id": catalog.customer.id,
                "start_date": "2026-05-01",
                "expiry_date": "2026-04-01",
            },
        ).status_code
        == 422
    )
    ok = client.post(
        url,
        json={"customer_id": catalog.customer.id, "start_date": "2026-05-01", "expiry_date": "2027-05-01"},
    )
    assert ok.status_code == 201 and ok.json()["expiry_date"] == "2027-05-01"
    assert (
        client.post(
            "/api/quotation-templates/99999/create-subscription", json={"customer_id": catalog.customer.id}
        ).status_code
        == 404
    )


def test_from_template_rejects_a_plan_that_is_no_longer_available(client, users, catalog, login, db):
    login("staff@t.test")
    tid = client.post("/api/quotation-templates", json=template_body(catalog)).json()["id"]
    catalog.monthly.available_to = TODAY - timedelta(days=1)
    db.commit()
    r = client.post(
        f"/api/quotation-templates/{tid}/create-subscription", json={"customer_id": catalog.customer.id}
    )
    assert r.status_code == 422 and r.json()["detail"][0]["loc"] == ["body", "plan_id"]


def test_from_template_rejects_products_that_became_inactive(client, users, catalog, login, db):
    login("staff@t.test")
    tid = client.post("/api/quotation-templates", json=template_body(catalog)).json()["id"]
    catalog.other.active = False
    db.commit()
    r = client.post(
        f"/api/quotation-templates/{tid}/create-subscription", json={"customer_id": catalog.customer.id}
    )
    assert r.status_code == 422
