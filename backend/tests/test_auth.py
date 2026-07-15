"""Tests for authentication and session management."""

from fastapi.testclient import TestClient

from conftest import (
    USER_A_LOGIN, USER_B_LOGIN, PASSWORD_A, PASSWORD_B,
    SECURITY_QUESTION, SECURITY_ANSWER,
)
from main import app


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


# ── Forgot password (bucket 08, item 8 — previously zero coverage) ──────


def test_forgot_password_question_returns_real_question_for_known_user(client):
    resp = client.post("/api/auth/forgot-password/question", json={"username": USER_A_LOGIN})
    assert resp.status_code == 200
    assert resp.json()["security_question"] == SECURITY_QUESTION


def test_forgot_password_question_does_not_reveal_unknown_usernames(client):
    """A nonexistent username still gets a plausible placeholder question
    (not a null/empty/different-shaped response) so the endpoint can't be
    used to enumerate which usernames are registered."""
    known = client.post("/api/auth/forgot-password/question", json={"username": USER_A_LOGIN})
    unknown = client.post("/api/auth/forgot-password/question", json={"username": "nobody"})
    assert known.status_code == unknown.status_code == 200
    assert isinstance(unknown.json()["security_question"], str)
    assert unknown.json()["security_question"]


def test_forgot_password_reset_rejects_wrong_answer(client):
    resp = client.post("/api/auth/forgot-password/reset", json={
        "username": USER_A_LOGIN, "security_answer": "wrong answer", "new_password": "newpass123",
    })
    assert resp.status_code == 401


def test_forgot_password_reset_rejects_unknown_username_with_same_error(client):
    """Same 401 (not 404) for an unknown username as for a wrong answer —
    otherwise the status code itself would leak which usernames exist."""
    resp = client.post("/api/auth/forgot-password/reset", json={
        "username": "nobody", "security_answer": "whatever", "new_password": "newpass123",
    })
    assert resp.status_code == 401


def test_forgot_password_reset_succeeds_and_allows_login_with_new_password(client):
    resp = client.post("/api/auth/forgot-password/reset", json={
        "username": USER_A_LOGIN, "security_answer": SECURITY_ANSWER, "new_password": "newpass123",
    })
    assert resp.status_code == 200

    login = client.post("/api/auth/login", json={
        "username": USER_A_LOGIN, "password": "newpass123",
    })
    assert login.status_code == 200
    # The old password must no longer work.
    old_login = client.post("/api/auth/login", json={
        "username": USER_A_LOGIN, "password": PASSWORD_A,
    })
    assert old_login.status_code == 401


def test_forgot_password_reset_answer_is_case_and_whitespace_insensitive(client):
    resp = client.post("/api/auth/forgot-password/reset", json={
        "username": USER_A_LOGIN, "security_answer": "  BLUE  ", "new_password": "newpass123",
    })
    assert resp.status_code == 200


def test_forgot_password_reset_invalidates_existing_sessions(client):
    """A password reset must invalidate any session that was already logged
    in before the reset (session_version bump) — otherwise a stolen/leaked
    session survives a password reset meant to lock it out."""
    login = client.post("/api/auth/login", json={"username": USER_A_LOGIN, "password": PASSWORD_A})
    assert login.status_code == 200
    assert client.get("/api/auth/me").status_code == 200

    reset = client.post("/api/auth/forgot-password/reset", json={
        "username": USER_A_LOGIN, "security_answer": SECURITY_ANSWER, "new_password": "newpass123",
    })
    assert reset.status_code == 200

    assert client.get("/api/auth/me").status_code == 401


def test_forgot_password_reset_rate_limited_after_five_failures(client):
    for _ in range(5):
        resp = client.post("/api/auth/forgot-password/reset", json={
            "username": USER_A_LOGIN, "security_answer": "wrong", "new_password": "newpass123",
        })
        assert resp.status_code == 401

    # 6th attempt is rate-limited even with the *correct* answer.
    resp = client.post("/api/auth/forgot-password/reset", json={
        "username": USER_A_LOGIN, "security_answer": SECURITY_ANSWER, "new_password": "newpass123",
    })
    assert resp.status_code == 429


def test_forgot_password_rate_limit_is_scoped_per_username(client):
    """A lockout on one username must not block resets for the other."""
    for _ in range(5):
        client.post("/api/auth/forgot-password/reset", json={
            "username": USER_A_LOGIN, "security_answer": "wrong", "new_password": "x",
        })

    resp = client.post("/api/auth/forgot-password/reset", json={
        "username": USER_B_LOGIN, "security_answer": SECURITY_ANSWER, "new_password": "newpass123",
    })
    assert resp.status_code == 200


def test_forgot_password_successful_reset_clears_the_rate_limit_counter(client):
    """A successful reset must clear the attempt counter — otherwise 4
    earlier typos plus one correct reset would still count toward a
    lockout on the *next* legitimate reset need."""
    for _ in range(4):
        client.post("/api/auth/forgot-password/reset", json={
            "username": USER_A_LOGIN, "security_answer": "wrong", "new_password": "x",
        })
    ok = client.post("/api/auth/forgot-password/reset", json={
        "username": USER_A_LOGIN, "security_answer": SECURITY_ANSWER, "new_password": "newpass123",
    })
    assert ok.status_code == 200

    # A second legitimate reset request right after must not be blocked.
    again = client.post("/api/auth/forgot-password/reset", json={
        "username": USER_A_LOGIN, "security_answer": SECURITY_ANSWER, "new_password": "anotherpass456",
    })
    assert again.status_code == 200


# ── Session-version invalidation (bucket 08, item 8) ─────────────────────
# session_version is bumped on password change and forgot-password reset;
# _verify_token rejects any token whose embedded "sv" no longer matches.
# The forgot-password test above already covers the reset path — these
# cover change-password, and that it's scoped to *other* sessions only.


def test_change_password_invalidates_other_sessions(auth_client_a):
    """Changing your password from one session must sign out every other
    session holding an older (now stale) session_version — e.g. a second
    device, or an attacker with a copied cookie."""
    other_device = TestClient(app)
    login = other_device.post("/api/auth/login", json={
        "username": USER_A_LOGIN, "password": PASSWORD_A,
    })
    assert login.status_code == 200
    assert other_device.get("/api/auth/me").status_code == 200

    resp = auth_client_a.put("/api/auth/change-password", json={
        "current_password": PASSWORD_A, "new_password": "newpass123",
    })
    assert resp.status_code == 200

    # The other device's now-stale session must be rejected...
    assert other_device.get("/api/auth/me").status_code == 401
    # ...while the session that made the change keeps working (it was
    # transparently reissued with the bumped session_version inline).
    assert auth_client_a.get("/api/auth/me").status_code == 200
