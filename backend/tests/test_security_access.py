"""Tests for bucket 06 — Backend Security & Access Hardening.

Covers: SPA path-traversal containment (item 1), the personal-mode lockout
footgun — mode-switch restriction + honest login error (item 2), the
insecure-cookie startup warning (item 3), and sliding session expiry (item 5).
Item 4 (avatar delete-before-commit ordering) is covered in
test_account_deletion.py alongside the rest of that endpoint's tests.
"""

import http.cookies
import json
import logging
import time

import pytest

import auth as auth_mod
import main as main_mod
from conftest import USER_A_LOGIN, USER_B_LOGIN, PASSWORD_A, PASSWORD_B


def _set_mode(auth_client, mode):
    return auth_client.put("/api/settings", json={"app_mode": mode})


# ── 1. SPA path-traversal containment ──────────────────────────────────────
# frontend/dist doesn't exist in this environment, so the real serve_spa
# route never registers (it's conditional on FRONTEND_DIST.exists() at import
# time). The containment check is factored into resolve_spa_path() precisely
# so it can be exercised directly without a built frontend.


def test_resolve_spa_path_serves_file_inside_dist(tmp_path):
    dist_dir = tmp_path / "dist"
    (dist_dir / "assets").mkdir(parents=True)
    app_js = dist_dir / "assets" / "app.js"
    app_js.write_text("console.log('hi')")

    result = main_mod.resolve_spa_path(
        "assets/app.js", dist_dir=dist_dir, dist_dir_resolved=dist_dir.resolve()
    )
    assert result == app_js.resolve()


def test_resolve_spa_path_contained_but_missing_falls_through(tmp_path):
    """A client-side route with no matching file is still 'contained' — the
    caller (serve_spa) is responsible for falling back to index.html, this
    function just reports containment."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()

    result = main_mod.resolve_spa_path(
        "some/client/route", dist_dir=dist_dir, dist_dir_resolved=dist_dir.resolve()
    )
    assert result is not None
    assert not result.is_file()


def test_resolve_spa_path_blocks_traversal_to_sibling_file(tmp_path):
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    secret = tmp_path / ".env"
    secret.write_text("SECRET_KEY=super-secret")

    result = main_mod.resolve_spa_path(
        "../.env", dist_dir=dist_dir, dist_dir_resolved=dist_dir.resolve()
    )
    assert result is None


def test_resolve_spa_path_blocks_deep_traversal_to_db_file(tmp_path):
    dist_dir = tmp_path / "frontend" / "dist"
    dist_dir.mkdir(parents=True)
    db_file = tmp_path / "backend" / "mosaic.db"
    db_file.parent.mkdir(parents=True)
    db_file.write_text("not a real sqlite file")

    result = main_mod.resolve_spa_path(
        "../../backend/mosaic.db", dist_dir=dist_dir, dist_dir_resolved=dist_dir.resolve()
    )
    assert result is None


def test_resolve_spa_path_blocks_traversal_that_still_resolves_to_a_real_file(tmp_path):
    """Escaping the dist dir must be blocked even when the escaped target
    genuinely exists — the fix must not accidentally only catch escapes to
    nonexistent paths."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("should never be served")

    result = main_mod.resolve_spa_path(
        "../outside.txt", dist_dir=dist_dir, dist_dir_resolved=dist_dir.resolve()
    )
    assert result is None


# ── 2. Lockout footgun #1: personal-mode switching & honest login error ────


def test_secondary_user_cannot_switch_to_personal_mode(auth_client_b):
    resp = _set_mode(auth_client_b, "personal")
    assert resp.status_code == 403
    assert "primary" in resp.json()["detail"].lower()


def test_primary_user_can_switch_to_personal_mode(auth_client_a):
    resp = _set_mode(auth_client_a, "personal")
    assert resp.status_code == 200
    assert resp.json()["app_mode"] == "personal"


def test_rejected_personal_switch_leaves_mode_unchanged(auth_client_a, auth_client_b):
    _set_mode(auth_client_b, "personal")
    resp = auth_client_a.get("/api/settings")
    assert resp.json()["app_mode"] == "shared"


def test_login_blocked_by_personal_mode_gets_honest_error(auth_client_a, client):
    _set_mode(auth_client_a, "personal")
    resp = client.post(
        "/api/auth/login", json={"username": USER_B_LOGIN, "password": PASSWORD_B}
    )
    assert resp.status_code == 403
    assert "personal mode" in resp.json()["detail"].lower()


def test_login_unknown_user_in_personal_mode_stays_generic(auth_client_a, client):
    """A nonexistent username must not receive the mode-specific message —
    that would let an attacker distinguish real accounts from fake ones."""
    _set_mode(auth_client_a, "personal")
    resp = client.post(
        "/api/auth/login", json={"username": "nobody", "password": "whatever"}
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid username or password"


def test_login_wrong_password_for_primary_in_personal_mode_still_generic_401(auth_client_a, client):
    _set_mode(auth_client_a, "personal")
    resp = client.post(
        "/api/auth/login", json={"username": USER_A_LOGIN, "password": "wrongpass"}
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid username or password"


# ── 3. Insecure-cookie startup warning ──────────────────────────────────────


def test_warns_when_production_and_secure_cookie(monkeypatch, caplog):
    monkeypatch.setattr(main_mod, "IS_DEV", False)
    monkeypatch.setattr(main_mod, "COOKIE_SECURE", True)
    with caplog.at_level(logging.WARNING, logger="mosaic"):
        main_mod._warn_if_insecure_cookie_config()
    assert any("Insecure cookie configuration" in r.message for r in caplog.records)


def test_no_warning_when_cookie_secure_false(monkeypatch, caplog):
    monkeypatch.setattr(main_mod, "IS_DEV", False)
    monkeypatch.setattr(main_mod, "COOKIE_SECURE", False)
    with caplog.at_level(logging.WARNING, logger="mosaic"):
        main_mod._warn_if_insecure_cookie_config()
    assert not any("Insecure cookie configuration" in r.message for r in caplog.records)


def test_no_warning_in_dev_even_with_secure_cookie(monkeypatch, caplog):
    monkeypatch.setattr(main_mod, "IS_DEV", True)
    monkeypatch.setattr(main_mod, "COOKIE_SECURE", True)
    with caplog.at_level(logging.WARNING, logger="mosaic"):
        main_mod._warn_if_insecure_cookie_config()
    assert not any("Insecure cookie configuration" in r.message for r in caplog.records)


# ── 5. Sliding session expiry ───────────────────────────────────────────────


def _cookie_value_from_response(resp, name):
    """Pull a cookie's value straight off this response's own Set-Cookie
    header, correctly un-escaping the quoting our JSON-shaped token value
    triggers (commas/quotes force http.cookies to backslash-escape them).
    resp.cookies leaves that escaping raw; the client jar's .get() works but
    can raise CookieConflict once a manually-seeded and a server-reissued
    cookie of the same name both sit in the jar (see the two tests below)."""
    jar = http.cookies.SimpleCookie()
    jar.load(resp.headers["set-cookie"])
    return jar[name].value


def _stale_token(username, session_version, age_seconds, persist=False):
    payload = json.dumps({
        "user": username,
        "ts": int(time.time()) - age_seconds,
        "persist": persist,
        "sv": session_version,
    })
    sig = auth_mod._sign(payload)
    return f"{payload}|{sig}"


def test_fresh_session_is_not_refreshed(auth_client_a):
    resp = auth_client_a.get("/api/auth/me")
    assert resp.status_code == 200
    assert "set-cookie" not in resp.headers


def test_stale_non_persistent_session_is_refreshed(client, db):
    from users import get_user_by_username

    user = get_user_by_username(db, USER_A_LOGIN)
    age = auth_mod.SESSION_REFRESH_THRESHOLD + 60
    token = _stale_token(USER_A_LOGIN, user.session_version, age)
    client.cookies.set(auth_mod.SESSION_COOKIE, token)

    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["username"] == USER_A_LOGIN
    assert "set-cookie" in resp.headers

    new_token = _cookie_value_from_response(resp, auth_mod.SESSION_COOKIE)
    assert new_token != token
    new_payload = json.loads(new_token.rsplit("|", 1)[0])
    assert time.time() - new_payload["ts"] < 5  # freshly reissued, not the stale ts
    assert new_payload["persist"] is False


def test_persistent_session_is_not_refreshed_even_when_stale(client, db):
    """'Stay signed in' sessions already last a year — sliding refresh is
    only needed for the 8h default session, so persistent ones are left
    alone rather than churning a Set-Cookie header on every request forever."""
    from users import get_user_by_username

    user = get_user_by_username(db, USER_A_LOGIN)
    age = auth_mod.SESSION_REFRESH_THRESHOLD + 60
    token = _stale_token(USER_A_LOGIN, user.session_version, age, persist=True)
    client.cookies.set(auth_mod.SESSION_COOKIE, token)

    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    assert "set-cookie" not in resp.headers


def test_expired_non_persistent_session_still_rejected(client, db):
    """Sliding expiry must not let a session outlive SESSION_TTL entirely —
    only activity *within* the window extends it, it can't resurrect a
    session that's already fully expired."""
    from users import get_user_by_username

    user = get_user_by_username(db, USER_A_LOGIN)
    token = _stale_token(USER_A_LOGIN, user.session_version, auth_mod.SESSION_TTL + 60)
    client.cookies.set(auth_mod.SESSION_COOKIE, token)

    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_refreshed_session_survives_past_original_ttl(client, db):
    """The actual point of the fix: a cookie that's stale-but-refreshed
    keeps authenticating even after the *original* issuance would have
    expired under the old fixed-TTL behavior."""
    from users import get_user_by_username

    user = get_user_by_username(db, USER_A_LOGIN)
    # Just past the refresh threshold, comfortably inside SESSION_TTL.
    token = _stale_token(USER_A_LOGIN, user.session_version, auth_mod.SESSION_REFRESH_THRESHOLD + 60)
    client.cookies.set(auth_mod.SESSION_COOKIE, token)
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200

    # Simulate that the *original* token would now be expired (well past
    # SESSION_TTL from its original ts), but the client is holding the
    # refreshed cookie from the previous request instead. Read it off the
    # response directly (see _cookie_value_from_response), then set it
    # explicitly so the follow-up request definitely sends the refreshed
    # value, not whichever of the two same-name jar entries httpx picks.
    refreshed_token = _cookie_value_from_response(resp, auth_mod.SESSION_COOKIE)
    refreshed_payload = json.loads(refreshed_token.rsplit("|", 1)[0])
    assert time.time() - refreshed_payload["ts"] < auth_mod.SESSION_TTL

    client.cookies.set(auth_mod.SESSION_COOKIE, refreshed_token)
    resp2 = client.get("/api/auth/me")
    assert resp2.status_code == 200
