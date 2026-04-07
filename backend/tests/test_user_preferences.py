"""Tests for per-user date format preferences."""


def test_get_default_preferences(auth_client_a):
    """New users get DD/MM/YYYY as default date format."""
    resp = auth_client_a.get("/api/user-preferences")
    assert resp.status_code == 200
    assert resp.json()["date_format"] == "DD/MM/YYYY"


def test_update_date_format(auth_client_a):
    resp = auth_client_a.put("/api/user-preferences", json={
        "date_format": "MM/DD/YYYY",
    })
    assert resp.status_code == 200
    assert resp.json()["date_format"] == "MM/DD/YYYY"

    # Verify it persists
    resp = auth_client_a.get("/api/user-preferences")
    assert resp.json()["date_format"] == "MM/DD/YYYY"


def test_invalid_date_format_rejected(auth_client_a):
    resp = auth_client_a.put("/api/user-preferences", json={
        "date_format": "YYYY-MM-DD",
    })
    assert resp.status_code == 422


def test_per_user_isolation(auth_client_a, auth_client_b):
    """Each user has independent preferences."""
    auth_client_a.put("/api/user-preferences", json={"date_format": "MM/DD/YYYY"})
    auth_client_b.put("/api/user-preferences", json={"date_format": "YYYY/MM/DD"})

    assert auth_client_a.get("/api/user-preferences").json()["date_format"] == "MM/DD/YYYY"
    assert auth_client_b.get("/api/user-preferences").json()["date_format"] == "YYYY/MM/DD"


def test_update_overwrites(auth_client_a):
    """Updating twice uses the latest value."""
    auth_client_a.put("/api/user-preferences", json={"date_format": "MM/DD/YYYY"})
    auth_client_a.put("/api/user-preferences", json={"date_format": "YYYY/DD/MM"})
    assert auth_client_a.get("/api/user-preferences").json()["date_format"] == "YYYY/DD/MM"


def test_unauthenticated_rejected(client):
    resp = client.get("/api/user-preferences")
    assert resp.status_code == 401
