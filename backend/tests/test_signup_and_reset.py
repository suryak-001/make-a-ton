from sqlalchemy import select

from app.core.security import verify_password
from app.enums import Role
from app.models import Customer, PasswordResetToken, User
from app.models.base import utcnow

GOOD = {"name": "New Person", "email": "new@shop.test", "password": "Abcdef1!x"}


def test_signup_creates_customer_user_and_signs_in(client, db):
    r = client.post("/api/auth/signup", json=GOOD)
    assert r.status_code == 201
    body = r.json()
    assert body["role"] == "CUSTOMER" and body["customer_id"] is not None
    assert client.get("/api/auth/me").json()["email"] == "new@shop.test"  # cookie was set
    user = db.scalar(select(User).where(User.email == "new@shop.test"))
    assert user.password_hash != GOOD["password"] and verify_password(GOOD["password"], user.password_hash)


def test_signup_ignores_role_and_normalizes_email(client, db):
    r = client.post("/api/auth/signup", json={**GOOD, "email": "  MiXed@Shop.TEST ", "role": "ADMIN"})
    assert r.status_code == 201
    assert r.json()["role"] == "CUSTOMER" and r.json()["email"] == "mixed@shop.test"


def test_each_email_can_only_have_one_account(client, users):
    r = client.post("/api/auth/signup", json={**GOOD, "email": "STAFF@t.test"})
    assert r.status_code == 409
    assert r.json()["detail"][0]["loc"] == ["body", "email"]


def test_signup_enforces_password_policy(client):
    for bad in [
        "Abcdef1!",
        "abcdefg1!x",
        "ABCDEFG1!X",
        "Abcdefgh1x",
    ]:  # 8 chars / no upper / no lower / no special
        r = client.post("/api/auth/signup", json={**GOOD, "password": bad})
        assert r.status_code == 422, bad
        assert r.json()["detail"][0]["loc"][-1] == "password"


def test_signup_rejects_bad_email(client):
    assert client.post("/api/auth/signup", json={**GOOD, "email": "not-an-email"}).status_code == 422


def test_signup_links_existing_customer_record(client, db):
    existing = Customer(name="Pre-made", email="new@shop.test")
    db.add(existing)
    db.commit()
    client.post("/api/auth/signup", json=GOOD)
    db.refresh(existing)
    assert existing.user_id is not None
    assert len(db.scalars(select(Customer).where(Customer.email == "new@shop.test")).all()) == 1


def _token_from_mail(monkeypatch):
    sent = []
    monkeypatch.setattr("app.routers.auth.send_mail", lambda to, subject, body: sent.append((to, body)))
    return sent


def test_forgot_password_emails_link_to_registered_address(client, users, monkeypatch):
    sent = _token_from_mail(monkeypatch)
    r = client.post("/api/auth/forgot-password", json={"email": "Cust@t.test"})
    assert r.status_code == 202
    assert len(sent) == 1 and sent[0][0] == "cust@t.test" and "/reset-password?token=" in sent[0][1]


def test_forgot_password_does_not_reveal_unknown_emails(client, users, monkeypatch):
    sent = _token_from_mail(monkeypatch)
    known = client.post("/api/auth/forgot-password", json={"email": "cust@t.test"})
    unknown = client.post("/api/auth/forgot-password", json={"email": "nobody@t.test"})
    assert (known.status_code, known.json()) == (unknown.status_code, unknown.json())
    assert len(sent) == 1  # nothing was sent for the unknown address


def _issue_token(client, monkeypatch, email="cust@t.test"):
    sent = _token_from_mail(monkeypatch)
    client.post("/api/auth/forgot-password", json={"email": email})
    return sent[-1][1].split("token=")[1].split()[0]


def test_reset_password_works_once(client, users, monkeypatch, login):
    token = _issue_token(client, monkeypatch)
    new = "Brand-New1!"
    assert client.post("/api/auth/reset-password", json={"token": token, "password": new}).status_code == 204
    assert login("cust@t.test", new).status_code == 200
    assert login("cust@t.test").status_code == 401  # old password no longer works
    again = client.post("/api/auth/reset-password", json={"token": token, "password": "Another-1!x"})
    assert again.status_code == 422  # single use


def test_reset_rejects_unknown_expired_and_superseded_tokens(client, users, db, monkeypatch):
    new = "Brand-New1!"
    assert client.post("/api/auth/reset-password", json={"token": "nope", "password": new}).status_code == 422

    old = _issue_token(client, monkeypatch)
    newest = _issue_token(client, monkeypatch)  # supersedes `old`
    assert client.post("/api/auth/reset-password", json={"token": old, "password": new}).status_code == 422

    record = db.scalar(select(PasswordResetToken).where(PasswordResetToken.used_at.is_(None)))
    record.expires_at = utcnow().replace(year=2000)
    db.commit()
    assert client.post("/api/auth/reset-password", json={"token": newest, "password": new}).status_code == 422


def test_reset_enforces_password_policy_and_keeps_token_usable(client, users, monkeypatch, login):
    token = _issue_token(client, monkeypatch)
    assert (
        client.post("/api/auth/reset-password", json={"token": token, "password": "weak"}).status_code == 422
    )
    assert (
        client.post("/api/auth/reset-password", json={"token": token, "password": "Strong-Pass1"}).status_code
        == 204
    )
    assert login("cust@t.test", "Strong-Pass1").status_code == 200


def test_staff_role_unaffected(users):
    assert users["staff"].role == Role.STAFF
