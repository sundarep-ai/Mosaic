"""Tests for authentication and session management."""

from conftest import USER_A_LOGIN, USER_B_LOGIN, PASSWORD_A, PASSWORD_B


def test_login_valid_user_a(client):
    resp = client.post("/api/auth/login", json={
        "username": USER_A_LOGIN, "password": PASSWORD_A,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == USER_A_LOGIN
    assert data["display_name"] == "Alice"
    assert "user_map" in data


def test_login_valid_user_b(client):
    resp = client.post("/api/auth/login", json={
        "username": USER_B_LOGIN, "password": PASSWORD_B,
    })
    assert resp.status_code == 200
    assert resp.json()["username"] == USER_B_LOGIN
    assert resp.json()["display_name"] == "Bob"


def test_login_wrong_password(client):
    resp = client.post("/api/auth/login", json={
        "username": USER_A_LOGIN, "password": "wrong",
    })
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post("/api/auth/login", json={
        "username": "nobody", "password": "pass",
    })
    assert resp.status_code == 401


def test_unauthenticated_access(client):
    resp = client.get("/api/expenses")
    assert resp.status_code == 401


def test_me_endpoint(auth_client_a):
    resp = auth_client_a.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == USER_A_LOGIN
    assert data["display_name"] == "Alice"
    assert USER_A_LOGIN in data["user_map"]
    assert USER_B_LOGIN in data["user_map"]


def test_logout_clears_session(client):
    client.post("/api/auth/login", json={
        "username": USER_A_LOGIN, "password": PASSWORD_A,
    })
    assert client.get("/api/auth/me").status_code == 200
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401


def test_config_endpoint_no_auth_required(client):
    resp = client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["userA"] == "Alice"
    assert data["userB"] == "Bob"


# ── Cookie Flags (CR-3) ──────────────────────────────────────────────


def test_login_sets_cookie_with_httponly_and_max_age(client):
    """Session cookie must have httponly and max_age set."""
    resp = client.post("/api/auth/login", json={
        "username": USER_A_LOGIN, "password": PASSWORD_A,
    })
    assert resp.status_code == 200
    cookie = resp.headers.get("set-cookie", "")
    assert "httponly" in cookie.lower()
    assert "max-age" in cookie.lower()
