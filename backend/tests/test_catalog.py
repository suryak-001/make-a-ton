from datetime import date, timedelta

from sqlalchemy import select

from app.enums import AmountKind, BillingPeriod
from app.models import Plan, Product, QuotationTemplate, QuotationTemplateLine, Tax


def product_body(**over):
    body = {
        "name": "Brightloop CRM",
        "type": "SERVICE",
        "sales_price": "1200",
        "cost_price": "300",
        "notes": "  per seat  ",
        "variants": [
            {"attribute": "Brand", "value": "Standard", "extra_price": "0"},
            {"attribute": "Brand", "value": "Odoo", "extra_price": "560"},
        ],
    }
    return {**body, **over}


def test_products_are_admin_write_staff_read(client, users, login):
    login("staff@t.test")
    assert client.post("/api/products", json=product_body()).status_code == 403
    login("admin@t.test")
    created = client.post("/api/products", json=product_body())
    assert created.status_code == 201
    pid = created.json()["id"]
    login("staff@t.test")
    assert client.get(f"/api/products/{pid}").status_code == 200
    assert client.get("/api/products").json()["total"] == 1
    assert client.put(f"/api/products/{pid}", json=product_body()).status_code == 403
    assert client.delete(f"/api/products/{pid}").status_code == 403
    login("cust@t.test")
    assert client.get("/api/products").status_code == 403


def test_product_with_odoo_variant_adds_560(client, users, login):
    login("admin@t.test")
    body = client.post("/api/products", json=product_body()).json()
    odoo = next(v for v in body["variants"] if v["value"] == "Odoo")
    assert odoo["extra_price"] == "560.00" and body["notes"] == "per seat"
    assert body["sales_price"] == "1200.00"


def test_product_validation(client, users, login):
    login("admin@t.test")
    assert client.post("/api/products", json=product_body(sales_price="-1")).status_code == 422
    assert client.post("/api/products", json=product_body(sales_price="1.234")).status_code == 422
    assert client.post("/api/products", json=product_body(name="  ")).status_code == 422
    dup = [{"attribute": "Brand", "value": "Odoo"}, {"attribute": "brand", "value": "ODOO"}]
    assert client.post("/api/products", json=product_body(variants=dup)).status_code == 422
    assert client.post("/api/products", json=product_body(default_tax_ids=[999])).status_code == 422


def test_update_syncs_variants_and_taxes(client, users, login, db):
    tax = Tax(name="GST", kind=AmountKind.PERCENT, rate=18)
    db.add(tax)
    db.commit()
    login("admin@t.test")
    p = client.post("/api/products", json=product_body()).json()
    keep = next(v for v in p["variants"] if v["value"] == "Odoo")
    body = product_body(
        variants=[
            {"id": keep["id"], "attribute": "Brand", "value": "Odoo", "extra_price": "600"},
            {"attribute": "Edition", "value": "Pro", "extra_price": "100"},
        ],
        default_tax_ids=[tax.id],
    )
    out = client.put(f"/api/products/{p['id']}", json=body).json()
    assert {(v["value"], v["extra_price"]) for v in out["variants"]} == {
        ("Odoo", "600.00"),
        ("Pro", "100.00"),
    }
    assert out["variants"][0]["id"] == keep["id"] or any(v["id"] == keep["id"] for v in out["variants"])
    assert [t["name"] for t in out["default_taxes"]] == ["GST"]
    foreign = client.put(
        f"/api/products/{p['id']}",
        json=product_body(variants=[{"id": 99999, "attribute": "a", "value": "b"}]),
    )
    assert foreign.status_code == 422


def test_product_search_and_active_filter(client, users, login):
    login("admin@t.test")
    client.post("/api/products", json=product_body(name="Alpha"))
    client.post("/api/products", json=product_body(name="Beta", active=False))
    assert client.get("/api/products?q=alp").json()["total"] == 1
    assert client.get("/api/products?active=true").json()["total"] == 1
    assert client.get("/api/products?active=false").json()["items"][0]["name"] == "Beta"


def test_cannot_delete_or_unlink_product_used_elsewhere(client, users, login, db):
    login("admin@t.test")
    p = client.post("/api/products", json=product_body()).json()
    plan = Plan(name="M", price=0, billing_period=BillingPeriod.MONTHLY)
    db.add(plan)
    db.flush()
    template = QuotationTemplate(name="T", plan_id=plan.id)
    db.add(template)
    db.flush()
    variant_id = p["variants"][0]["id"]
    db.add(
        QuotationTemplateLine(template_id=template.id, product_id=p["id"], variant_id=variant_id, quantity=1)
    )
    db.commit()
    assert client.delete(f"/api/products/{p['id']}").status_code == 409
    drop_all_variants = client.put(f"/api/products/{p['id']}", json=product_body(variants=[]))
    assert drop_all_variants.status_code == 409
    assert db.get(Product, p["id"]) is not None
    assert len(client.get(f"/api/products/{p['id']}").json()["variants"]) == 2  # nothing was lost


def plan_body(**over):
    return {"name": "Monthly", "price": "0", "billing_period": "MONTHLY", **over}


def test_plans_admin_write_staff_read(client, users, login):
    login("staff@t.test")
    assert client.post("/api/plans", json=plan_body()).status_code == 403
    login("admin@t.test")
    r = client.post("/api/plans", json=plan_body(pausable=True, auto_close=True, min_quantity=5))
    assert r.status_code == 201
    body = r.json()
    assert (
        body["pausable"],
        body["auto_close"],
        body["closable"],
        body["renewable"],
        body["min_quantity"],
    ) == (
        True,
        True,
        True,
        True,
        5,
    )
    login("staff@t.test")
    assert client.get(f"/api/plans/{body['id']}").status_code == 200


def test_plan_validation_and_all_four_periods(client, users, login):
    login("admin@t.test")
    for period in ("DAILY", "WEEKLY", "MONTHLY", "YEARLY"):
        assert client.post("/api/plans", json=plan_body(billing_period=period)).status_code == 201
    assert client.post("/api/plans", json=plan_body(billing_period="HOURLY")).status_code == 422
    assert client.post("/api/plans", json=plan_body(min_quantity=0)).status_code == 422
    backwards = plan_body(available_from="2026-06-01", available_to="2026-05-01")
    assert client.post("/api/plans", json=backwards).status_code == 422


def test_available_filter_respects_window_and_active(client, users, login):
    login("admin@t.test")
    today = date.today()
    mk = lambda **kw: client.post("/api/plans", json=plan_body(**kw))  # noqa: E731
    mk(name="open")
    mk(
        name="current",
        available_from=str(today - timedelta(days=1)),
        available_to=str(today + timedelta(days=1)),
    )
    mk(name="ended", available_to=str(today - timedelta(days=1)))
    mk(name="future", available_from=str(today + timedelta(days=1)))
    mk(name="off", active=False)
    names = {p["name"] for p in client.get("/api/plans?available=true").json()["items"]}
    assert names == {"open", "current"}
    assert client.get("/api/plans").json()["total"] == 5


def test_plan_update_delete_and_in_use_conflict(client, users, login, db):
    login("admin@t.test")
    pid = client.post("/api/plans", json=plan_body()).json()["id"]
    assert (
        client.put(f"/api/plans/{pid}", json=plan_body(name="Renamed", closable=False)).json()["closable"]
        is False
    )
    db.add(QuotationTemplate(name="T", plan_id=pid))
    db.commit()
    assert client.delete(f"/api/plans/{pid}").status_code == 409
    free = client.post("/api/plans", json=plan_body(name="Free")).json()["id"]
    assert client.delete(f"/api/plans/{free}").status_code == 204
    assert db.scalar(select(Plan).where(Plan.id == free)) is None
