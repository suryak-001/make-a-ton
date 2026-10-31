"""Add-ons switched on and off on a live subscription, by staff and by the customer in the portal."""

from datetime import timedelta

from app.models import Customer, Product
from app.services.billing import generate_invoice_for_period
from tests.test_portal import TODAY, portal, staff_make


def make_addon(db, catalog, name="Analytics", price=400, **over):
    addon = Product(name=name, sales_price=price, is_addon=True, default_taxes=[catalog.gst], **over)
    db.add(addon)
    db.commit()
    return addon


def switch_on(client, sid, addon, quantity=1, base="/api/subscriptions"):
    return client.post(f"{base}/{sid}/addons", json={"product_id": addon.id, "quantity": quantity})


def test_staff_switch_an_addon_on_and_off(client, users, catalog, login, db):
    addon = make_addon(db, catalog)
    sub = staff_make(client, login, catalog)

    options = client.get(f"/api/subscriptions/{sub['id']}/addons").json()
    assert options["editable"] and [o["name"] for o in options["options"]] == ["Analytics"]
    assert options["options"][0]["line_id"] is None

    on = switch_on(client, sub["id"], addon, 2)
    assert on.status_code == 200, on.text
    line = next(x for x in on.json()["lines"] if x["product_id"] == addon.id)
    assert line["is_addon"] and line["quantity"] == 2 and line["amount"] == "944.00"  # 800 + 18%
    assert on.json()["events"][-1]["reason"] == "Add-on switched on: Analytics × 2"
    assert client.get(f"/api/subscriptions/{sub['id']}/addons").json()["options"][0]["line_id"] == line["id"]

    off = client.delete(f"/api/subscriptions/{sub['id']}/addons/{line['id']}")
    assert off.status_code == 200, off.text
    assert [x["product_id"] for x in off.json()["lines"]] == [catalog.crm.id]
    assert off.json()["events"][-1]["reason"] == "Add-on switched off: Analytics"


def test_the_next_invoice_carries_the_addon(client, users, catalog, login, db):
    addon = make_addon(db, catalog)
    sub = staff_make(client, login, catalog)
    switch_on(client, sub["id"], addon)
    invoice = generate_invoice_for_period(db, sub["id"], TODAY + timedelta(days=5))
    assert sorted(line.description for line in invoice.lines)[0].startswith("Analytics")
    assert len(invoice.lines) == 2


def test_only_addons_and_only_once(client, users, catalog, login, db):
    addon = make_addon(db, catalog)
    sub = staff_make(client, login, catalog)
    not_addon = client.post(f"/api/subscriptions/{sub['id']}/addons", json={"product_id": catalog.other.id})
    assert not_addon.status_code == 422
    assert switch_on(client, sub["id"], addon).status_code == 200
    again = switch_on(client, sub["id"], addon)
    assert again.status_code == 409 and "already switched on" in again.json()["detail"]

    main_line = client.get(f"/api/subscriptions/{sub['id']}").json()["lines"][0]
    refused = client.delete(f"/api/subscriptions/{sub['id']}/addons/{main_line['id']}")
    assert refused.status_code == 409 and "Only add-ons" in refused.json()["detail"]


def test_the_plan_minimum_applies_to_addons(client, users, catalog, login, db):
    addon = make_addon(db, catalog)
    sub = staff_make(client, login, catalog, catalog.strict)
    response = switch_on(client, sub["id"], addon, 1)
    assert response.status_code == 422 and "at least 5" in response.text


def test_addons_wait_while_the_subscription_is_not_live_or_billing_is_behind(
    client, users, catalog, login, db
):
    addon = make_addon(db, catalog)
    quote = staff_make(client, login, catalog, status="QUOTATION")
    assert switch_on(client, quote["id"], addon).status_code == 409
    assert not client.get(f"/api/subscriptions/{quote['id']}/addons").json()["editable"]

    behind = staff_make(client, login, catalog, start_date=str(TODAY - timedelta(days=40)))
    response = switch_on(client, behind["id"], addon)
    assert response.status_code == 409 and "Billing is behind" in response.json()["detail"]


def test_customer_switches_addons_on_their_own_subscription_only(client, users, catalog, login, db):
    addon = make_addon(db, catalog)
    mine = staff_make(client, login, catalog)
    rival = Customer(name="Rival", email="rival@x.test")
    db.add(rival)
    db.commit()
    theirs = staff_make(client, login, catalog, customer=rival)

    portal(client, login)
    base = "/api/portal-subscriptions"
    assert client.get(f"{base}/{mine['id']}/addons").json()["options"][0]["name"] == "Analytics"
    on = switch_on(client, mine["id"], addon, base=base)
    assert on.status_code == 200, on.text
    assert on.json()["events"][-1]["actor_name"] is None  # staff names never reach the portal
    line_id = next(x["id"] for x in on.json()["lines"] if x["is_addon"])
    assert client.delete(f"{base}/{mine['id']}/addons/{line_id}").status_code == 200

    assert client.get(f"{base}/{theirs['id']}/addons").status_code == 404
    assert switch_on(client, theirs["id"], addon, base=base).status_code == 404


def test_inactive_addons_are_not_offered(client, users, catalog, login, db):
    make_addon(db, catalog, active=False)
    sub = staff_make(client, login, catalog)
    assert client.get(f"/api/subscriptions/{sub['id']}/addons").json()["options"] == []
