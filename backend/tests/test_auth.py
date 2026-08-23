"""Authentication flow tests."""


def test_login_success(client, admin_user):
    resp = client.post("/api/v1/auth/login", data={"username": "admin_test", "password": "AdminPass123"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"]
    tokens = body["data"]
    assert tokens["access_token"] and tokens["refresh_token"]


def test_login_wrong_password(client, admin_user):
    resp = client.post("/api/v1/auth/login", data={"username": "admin_test", "password": "wrong-pass"})
    assert resp.status_code == 401


def test_me_requires_token(client, admin_user):
    assert client.get("/api/v1/auth/me").status_code == 401

    tokens = client.post(
        "/api/v1/auth/login", data={"username": "admin_test", "password": "AdminPass123"}
    ).json()["data"]
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert resp.status_code == 200
    assert resp.json()["data"]["role"] == "admin"


def test_refresh_flow(client, admin_user):
    tokens = client.post(
        "/api/v1/auth/login", data={"username": "admin_test", "password": "AdminPass123"}
    ).json()["data"]

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    new_tokens = resp.json()["data"]
    assert new_tokens["access_token"] != tokens["access_token"]

    # Old refresh token must not be accepted as an access token.
    bad = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"})
    assert bad.status_code == 401


def test_inactive_user_cannot_login(client, admin_user, db):
    admin_user.is_active = False
    db.commit()

    resp = client.post("/api/v1/auth/login", data={"username": "admin_test", "password": "AdminPass123"})
    assert resp.status_code == 401
