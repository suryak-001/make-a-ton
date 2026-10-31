from app.core.security import password_problems
from app.services.sequence import next_number


def login(client, email, password="Passw0rd!x"):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_password_policy_matches_the_brief():
    assert password_problems("Abcdef1!x") == []
    assert password_problems("Abcdef!1") != []  # exactly 8 chars is not "more than eight"
    assert password_problems("abcdefgh!1") != []  # no uppercase
    assert password_problems("ABCDEFGH!1") != []  # no lowercase
    assert password_problems("Abcdefgh12") != []  # no special character


def test_login_me_logout(client, users):
    assert client.get("/api/auth/me").status_code == 401
    r = login(client, "STAFF@t.test")  # email is case-insensitive
    assert r.status_code == 200 and r.json()["role"] == "STAFF"
    assert client.get("/api/auth/me").json()["email"] == "staff@t.test"
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401


def test_login_rejects_bad_credentials(client, users):
    assert login(client, "staff@t.test", "wrong").status_code == 401
    assert login(client, "nobody@t.test").status_code == 401


def test_customer_login_exposes_customer_id(client, users):
    assert login(client, "cust@t.test").json()["customer_id"] is not None


def test_require_roles(client, users):
    from fastapi import Depends

    from app.core.deps import require_roles
    from app.enums import Role
    from app.main import app

    @app.get("/api/_test/admin-only")
    def admin_only(_=Depends(require_roles(Role.ADMIN))):
        return {"ok": True}

    assert client.get("/api/_test/admin-only").status_code == 401
    login(client, "staff@t.test")
    assert client.get("/api/_test/admin-only").status_code == 403
    login(client, "admin@t.test")
    assert client.get("/api/_test/admin-only").status_code == 200


def test_next_number_is_sequential(db):
    assert next_number(db, "T", "T-") == "T-00001"
    assert next_number(db, "T", "T-") == "T-00002"
    assert next_number(db, "T2", "X-", pad=3) == "X-001"


def test_pricing_preview_requires_login_and_matches_service(client, users):
    body = {
        "unit_price": "1000",
        "variant_extra": "560",
        "quantity": 2,
        "taxes": [{"kind": "PERCENT", "rate": "18"}],
    }
    assert client.post("/api/pricing/preview", json=body).status_code == 401
    login(client, "cust@t.test")
    r = client.post("/api/pricing/preview", json=body)
    assert r.status_code == 200
    assert r.json()["unit_price"] == "1560.00" and r.json()["total"] == "3681.60"
