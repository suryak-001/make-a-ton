from sqlalchemy import select

from app.enums import Role
from app.models import User


def test_only_admin_can_add_staff(client, users, login):
    body = {"name": "New Staffer", "email": "new.staff@t.test", "password": "Abcdef1!x"}
    assert client.post("/api/users", json=body).status_code == 401
    login("staff@t.test")
    assert client.post("/api/users", json=body).status_code == 403
    login("cust@t.test")
    assert client.post("/api/users", json=body).status_code == 403
    login("admin@t.test")
    r = client.post("/api/users", json=body)
    assert r.status_code == 201 and r.json()["role"] == "STAFF"


def test_new_staff_can_sign_in_with_limited_access(client, users, login, db):
    login("admin@t.test")
    client.post("/api/users", json={"name": "S2", "email": "s2@t.test", "password": "Abcdef1!x"})
    assert db.scalar(select(User).where(User.email == "s2@t.test")).role == Role.STAFF
    assert login("s2@t.test", "Abcdef1!x").json()["role"] == "STAFF"
    assert client.get("/api/users").status_code == 403  # staff cannot list or manage users
    assert client.get("/api/customers").status_code == 200  # but can handle customers


def test_add_staff_validates_password_and_duplicate_email(client, users, login):
    login("admin@t.test")
    weak = client.post("/api/users", json={"name": "X", "email": "x@t.test", "password": "weak"})
    assert weak.status_code == 422
    dup = client.post("/api/users", json={"name": "X", "email": "STAFF@t.test", "password": "Abcdef1!x"})
    assert dup.status_code == 409


def test_list_users_filters_and_paginates(client, users, login):
    login("admin@t.test")
    everyone = client.get("/api/users").json()
    assert everyone["total"] == 3
    assert client.get("/api/users?role=STAFF").json()["total"] == 1
    assert client.get("/api/users?q=cust").json()["total"] == 1
    assert len(client.get("/api/users?page=1&page_size=2").json()["items"]) == 2


def test_customer_crud_for_staff(client, users, login):
    login("staff@t.test")
    r = client.post(
        "/api/customers",
        json={"name": " Acme ", "email": "AP@Acme.test", "phone": "", "address": "1 Main St"},
    )
    assert r.status_code == 201
    c = r.json()
    assert (c["name"], c["email"], c["phone"], c["has_login"]) == ("Acme", "ap@acme.test", None, False)
    assert (
        client.put(f"/api/customers/{c['id']}", json={"name": "Acme Inc", "email": "ap@acme.test"}).json()[
            "name"
        ]
        == "Acme Inc"
    )
    assert client.get(f"/api/customers/{c['id']}").json()["name"] == "Acme Inc"
    assert client.get("/api/customers?q=acme").json()["total"] == 1
    assert client.delete(f"/api/customers/{c['id']}").status_code == 204
    assert client.get(f"/api/customers/{c['id']}").status_code == 404


def test_customers_are_not_available_to_portal_users(client, users, login):
    login("cust@t.test")
    assert client.get("/api/customers").status_code == 403


def test_customer_search_treats_wildcards_literally(client, users, login):
    login("staff@t.test")
    client.post("/api/customers", json={"name": "100% Organic", "email": "o@t.test"})
    assert client.get("/api/customers?q=%25").json()["total"] == 1  # only the name containing a literal %
    assert client.get("/api/customers?q=_").json()["total"] == 0


def test_cannot_delete_customer_with_login(client, users, login, db):
    login("staff@t.test")
    from app.models import Customer

    cid = db.scalar(select(Customer.id).where(Customer.email == "cust@t.test"))
    assert client.delete(f"/api/customers/{cid}").status_code == 409
