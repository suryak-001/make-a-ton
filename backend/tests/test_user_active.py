"""An admin can switch a staff member off; they are locked out straight away."""


def test_switched_off_staff_cannot_sign_in_or_use_a_session(client, users, login):
    login("staff@t.test")
    assert client.get("/api/auth/me").status_code == 200  # signed in
    other = client  # the same cookie jar is reused below, so sign in as admin afterwards
    login("admin@t.test")
    staff_id = next(u["id"] for u in other.get("/api/users").json()["items"] if u["email"] == "staff@t.test")
    r = client.patch(f"/api/users/{staff_id}/active", json={"active": False})
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert login("staff@t.test").status_code == 403
    r = client.patch(f"/api/users/{staff_id}/active", json={"active": True})
    assert r.json()["is_active"] is True
    assert login("staff@t.test").status_code == 200


def test_an_admin_cannot_switch_off_themselves_and_staff_cannot_switch_anyone(client, users, login):
    login("admin@t.test")
    me = client.get("/api/auth/me").json()["id"]
    assert client.patch(f"/api/users/{me}/active", json={"active": False}).status_code == 422
    login("staff@t.test")
    assert client.patch(f"/api/users/{me}/active", json={"active": False}).status_code == 403
