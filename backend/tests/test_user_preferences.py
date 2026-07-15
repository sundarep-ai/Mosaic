"""Tests for per-user preferences: date format, currency, income-mode toggle."""


def test_get_default_preferences(auth_client_a):
    """New users get the documented defaults for every preference."""
    resp = auth_client_a.get("/api/user-preferences")
    assert resp.status_code == 200
    body = resp.json()
    assert body["date_format"] == "DD/MM/YYYY"
    assert body["currency"] == "CAD"
    assert body["income_mode_enabled"] is False


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


def test_update_currency(auth_client_a):
    resp = auth_client_a.put("/api/user-preferences", json={"currency": "USD"})
    assert resp.status_code == 200
    assert resp.json()["currency"] == "USD"

    resp = auth_client_a.get("/api/user-preferences")
    assert resp.json()["currency"] == "USD"


def test_invalid_currency_rejected(auth_client_a):
    resp = auth_client_a.put("/api/user-preferences", json={"currency": "XYZ"})
    assert resp.status_code == 422


def test_update_income_mode_enabled(auth_client_a):
    resp = auth_client_a.put("/api/user-preferences", json={"income_mode_enabled": True})
    assert resp.status_code == 200
    assert resp.json()["income_mode_enabled"] is True

    resp = auth_client_a.get("/api/user-preferences")
    assert resp.json()["income_mode_enabled"] is True


def test_partial_update_leaves_other_fields_untouched(auth_client_a):
    """PUT-ing one field must not reset the others to their defaults."""
    auth_client_a.put("/api/user-preferences", json={"date_format": "MM/DD/YYYY"})
    auth_client_a.put("/api/user-preferences", json={"currency": "USD"})
    auth_client_a.put("/api/user-preferences", json={"income_mode_enabled": True})

    body = auth_client_a.get("/api/user-preferences").json()
    assert body["date_format"] == "MM/DD/YYYY"
    assert body["currency"] == "USD"
    assert body["income_mode_enabled"] is True


def test_per_user_isolation(auth_client_a, auth_client_b):
    """Each user has independent preferences."""
    auth_client_a.put("/api/user-preferences", json={"date_format": "MM/DD/YYYY", "currency": "USD"})
    auth_client_b.put("/api/user-preferences", json={"date_format": "YYYY/MM/DD", "currency": "EUR"})

    a = auth_client_a.get("/api/user-preferences").json()
    b = auth_client_b.get("/api/user-preferences").json()
    assert a["date_format"] == "MM/DD/YYYY"
    assert a["currency"] == "USD"
    assert b["date_format"] == "YYYY/MM/DD"
    assert b["currency"] == "EUR"


def test_update_overwrites(auth_client_a):
    """Updating twice uses the latest value."""
    auth_client_a.put("/api/user-preferences", json={"date_format": "MM/DD/YYYY"})
    auth_client_a.put("/api/user-preferences", json={"date_format": "YYYY/DD/MM"})
    assert auth_client_a.get("/api/user-preferences").json()["date_format"] == "YYYY/DD/MM"


def test_unauthenticated_rejected(client):
    resp = client.get("/api/user-preferences")
    assert resp.status_code == 401
