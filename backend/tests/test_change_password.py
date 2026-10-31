"""Staff an admin added choose their own password on first sign-in."""


def test_staff_added_by_admin_must_change_password(client, users, login):
    login("admin@t.test")
    r = client.post("/api/users", json={"name": "New Staff", "email": "ns@t.test", "password": "Temp@12345"})
    assert r.status_code == 201
    r = login("ns@t.test", "Temp@12345")
    assert r.json()["must_change_password"] is True


def test_changing_it_clears_the_flag(client, users, login):
    login("admin@t.test")
    client.post("/api/users", json={"name": "New Staff", "email": "ns@t.test", "password": "Temp@12345"})
    login("ns@t.test", "Temp@12345")
    r = client.post(
        "/api/auth/change-password", json={"current_password": "Temp@12345", "new_password": "Mine@67890"}
    )
    assert r.status_code == 204
    assert client.get("/api/auth/me").json()["must_change_password"] is False
    assert login("ns@t.test", "Mine@67890").status_code == 200


def test_wrong_current_password_or_weak_new_one_is_refused(client, users, login):
    login("staff@t.test")
    bad = client.post(
        "/api/auth/change-password", json={"current_password": "nope", "new_password": "Mine@67890"}
    )
    assert bad.status_code == 422 and bad.json()["detail"][0]["loc"] == ["body", "current_password"]
    weak = client.post(
        "/api/auth/change-password", json={"current_password": "Passw0rd!x", "new_password": "weak"}
    )
    assert weak.status_code == 422


def test_existing_users_are_not_forced(client, users, login):
    assert login("cust@t.test").json()["must_change_password"] is False
