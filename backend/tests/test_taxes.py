from datetime import date

from app.models import Product, Tax

TODAY = date.today()


def tax_body(**over):
    return {"name": "VAT 12%", "kind": "PERCENT", "rate": "12", **over}


def test_taxes_are_admin_write_staff_read(client, users, login):
    login("staff@t.test")
    assert client.post("/api/taxes", json=tax_body()).status_code == 403
    login("admin@t.test")
    created = client.post("/api/taxes", json=tax_body())
    assert created.status_code == 201
    tid = created.json()["id"]
    assert created.json()["rate"] == "12.00" and created.json()["active"] is True
    login("staff@t.test")
    assert client.get(f"/api/taxes/{tid}").status_code == 200
    assert client.get("/api/taxes").json()["total"] == 1
    assert client.put(f"/api/taxes/{tid}", json=tax_body()).status_code == 403
    assert client.delete(f"/api/taxes/{tid}").status_code == 403
    login("cust@t.test")
    assert client.get("/api/taxes").status_code == 403


def test_signed_out_is_401(client):
    assert client.get("/api/taxes").status_code == 401


def test_validation_names_the_field(client, users, login):
    login("admin@t.test")

    def field_of(r):
        assert r.status_code == 422, r.text
        return r.json()["detail"][0]["loc"][-1]

    assert field_of(client.post("/api/taxes", json=tax_body(name="  "))) == "name"
    assert field_of(client.post("/api/taxes", json=tax_body(rate="-1"))) == "rate"
    assert field_of(client.post("/api/taxes", json=tax_body(rate="1.234"))) == "rate"
    over = client.post("/api/taxes", json=tax_body(rate="101"))
    assert over.status_code == 422 and "100" in str(over.json())
    assert client.post("/api/taxes", json=tax_body(kind="BOGUS")).status_code == 422


def test_fixed_tax_may_exceed_100(client, users, login):
    login("admin@t.test")
    assert client.post("/api/taxes", json=tax_body(name="Levy", kind="FIXED", rate="250")).status_code == 201


def test_names_are_unique_ignoring_case(client, users, login):
    login("admin@t.test")
    first = client.post("/api/taxes", json=tax_body()).json()
    dup = client.post("/api/taxes", json=tax_body(name="vat 12%"))
    assert dup.status_code == 422 and dup.json()["detail"][0]["loc"] == ["body", "name"]
    other = client.post("/api/taxes", json=tax_body(name="Other")).json()
    clash = client.put(f"/api/taxes/{other['id']}", json=tax_body(name="VAT 12%"))
    assert clash.status_code == 422
    # Saving a tax under its own name is fine.
    assert client.put(f"/api/taxes/{first['id']}", json=tax_body(rate="15")).json()["rate"] == "15.00"


def test_list_filters_search_and_paginates(client, users, login):
    login("admin@t.test")
    for i in range(3):
        client.post("/api/taxes", json=tax_body(name=f"Tax {i}", active=i != 1))
    assert client.get("/api/taxes?active=true").json()["total"] == 2
    assert client.get("/api/taxes?active=false").json()["total"] == 1
    assert client.get("/api/taxes?q=tax 2").json()["total"] == 1
    page = client.get("/api/taxes?page_size=2").json()
    assert (len(page["items"]), page["total"]) == (2, 3)
    assert client.get("/api/taxes/9999").status_code == 404


def test_delete_unused_tax_unlinks_products(client, users, login, db):
    login("admin@t.test")
    tid = client.post("/api/taxes", json=tax_body()).json()["id"]
    product = Product(name="P", sales_price=10, default_taxes=[db.get(Tax, tid)])
    db.add(product)
    db.commit()
    assert client.delete(f"/api/taxes/{tid}").status_code == 204
    db.refresh(product)
    assert product.default_taxes == []
    assert client.get(f"/api/taxes/{tid}").status_code == 404


def test_delete_blocked_when_a_subscription_line_uses_it(client, users, catalog, login):
    from tests.test_subscriptions import make

    make(client, login, catalog)  # the CRM line carries GST 18%
    login("admin@t.test")
    r = client.delete(f"/api/taxes/{catalog.gst.id}")
    assert r.status_code == 409 and "inactive" in r.json()["detail"]


# ── the point of A1: a tax created by the admin changes a quote total ──


def quote_total(client, login, catalog, product):
    from tests.test_subscriptions import make

    sub = make(client, login, catalog, lines=[{"product_id": product.id, "quantity": 2}])
    return sub["tax_total"], sub["total"]


def test_new_tax_on_a_product_changes_the_quote_total(client, users, catalog, login):
    # "Other" has no tax: 2 x 50 = 100.00
    assert quote_total(client, login, catalog, catalog.other) == ("0.00", "100.00")

    login("admin@t.test")
    vat = client.post("/api/taxes", json=tax_body(name="VAT 10%", rate="10")).json()
    other = client.get(f"/api/products/{catalog.other.id}").json()
    body = {**other, "default_tax_ids": [vat["id"]]}
    assert client.put(f"/api/products/{catalog.other.id}", json=body).status_code == 200

    assert quote_total(client, login, catalog, catalog.other) == ("10.00", "110.00")


def test_fixed_tax_is_per_unit_and_inactive_tax_is_skipped(client, users, catalog, login):
    login("admin@t.test")
    levy = client.post("/api/taxes", json=tax_body(name="Levy", kind="FIXED", rate="3")).json()
    other = client.get(f"/api/products/{catalog.other.id}").json()
    client.put(f"/api/products/{catalog.other.id}", json={**other, "default_tax_ids": [levy["id"]]})
    assert quote_total(client, login, catalog, catalog.other) == ("6.00", "106.00")  # 3 x 2 units

    login("admin@t.test")
    client.put(f"/api/taxes/{levy['id']}", json=tax_body(name="Levy", kind="FIXED", rate="3", active=False))
    assert quote_total(client, login, catalog, catalog.other) == ("0.00", "100.00")


def test_changing_a_rate_does_not_touch_stored_quotes(client, users, catalog, login):
    from tests.test_subscriptions import make

    sub = make(client, login, catalog)
    login("admin@t.test")
    gst = client.get(f"/api/taxes/{catalog.gst.id}").json()
    client.put(f"/api/taxes/{gst['id']}", json={**gst, "rate": "28"})
    again = client.get(f"/api/subscriptions/{sub['id']}").json()
    assert again["tax_total"] == sub["tax_total"] == "561.60"
