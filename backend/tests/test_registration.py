"""Tests for the real registration flow's mode-forcing behavior (bucket 08,
item 5).

conftest's autouse fixture seeds two users directly into the DB for every
other test in this suite, bypassing the /api/auth/register endpoint
entirely — so the documented core behavior ("1st user forces personal,
2nd auto-switches to shared", CLAUDE.md) was never actually exercised
anywhere. These tests clear that seeded state and drive real registration
calls instead.
"""

from sqlalchemy import text

from conftest import set_mode


def _clear_users(db):
    db.execute(text("DELETE FROM user"))
    db.execute(text("DELETE FROM settings"))
    db.commit()


def _register_payload(username, display_name, password="testpass123"):
    return {
        "username": username,
        "display_name": display_name,
        "password": password,
        "security_question": "Favorite color?",
        "security_answer": "blue",
    }


def test_first_registration_forces_personal_mode(client, db):
    """Even if Settings already says "shared" (e.g. a stale row from a prior
    household), registering the very first user must force it back to
    "personal" — a fresh single-user install must never start shared."""
    _clear_users(db)
    set_mode(db, "shared")

    resp = client.post("/api/auth/register", json=_register_payload("alice2", "Alice Two"))
    assert resp.status_code == 201

    # /api/settings requires auth — log in first.
    login = client.post("/api/auth/login", json={"username": "alice2", "password": "testpass123"})
    assert login.status_code == 200
    settings = client.get("/api/settings")
    assert settings.json()["app_mode"] == "personal"


def test_second_registration_auto_switches_to_shared(client, db):
    """Registering a 2nd account must auto-switch the app to "shared" so
    both users can log in immediately, without a manual settings change."""
    _clear_users(db)

    first = client.post("/api/auth/register", json=_register_payload("alice2", "Alice Two"))
    assert first.status_code == 201

    login = client.post("/api/auth/login", json={"username": "alice2", "password": "testpass123"})
    assert login.status_code == 200
    assert client.get("/api/settings").json()["app_mode"] == "personal"

    second = client.post("/api/auth/register", json=_register_payload("bob2", "Bob Two"))
    assert second.status_code == 201

    assert client.get("/api/settings").json()["app_mode"] == "shared"


def test_registration_rejects_a_third_account(client, db):
    """The app caps out at 2 registered accounts — a 3rd attempt must be
    rejected outright, not silently accepted or left to corrupt the
    2-user assumptions baked into balance/mode logic."""
    _clear_users(db)

    assert client.post("/api/auth/register", json=_register_payload("alice2", "Alice Two")).status_code == 201
    assert client.post("/api/auth/register", json=_register_payload("bob2", "Bob Two")).status_code == 201

    third = client.post("/api/auth/register", json=_register_payload("carol", "Carol"))
    assert third.status_code == 409
    assert "Maximum of 2 accounts" in third.json()["detail"]

    # Mode must still be "shared" from the 2nd registration — a rejected
    # 3rd attempt must not have touched Settings at all.
    login = client.post("/api/auth/login", json={"username": "alice2", "password": "testpass123"})
    assert login.status_code == 200
    assert client.get("/api/settings").json()["app_mode"] == "shared"


def test_registered_user_can_log_in_immediately(client, db):
    """Sanity check that the registration flow used above actually produces
    a usable account — a mode-forcing bug that also broke login would be
    easy to miss if the rest of this file only ever checked /api/settings."""
    _clear_users(db)

    client.post("/api/auth/register", json=_register_payload("alice2", "Alice Two"))
    resp = client.post("/api/auth/login", json={"username": "alice2", "password": "testpass123"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "alice2"
