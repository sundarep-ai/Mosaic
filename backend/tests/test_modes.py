"""
Tests for multi-mode support (personal / shared / blended).

Covers: Settings API, mode-aware validation, personal login restriction,
personal balance stub, personal-summary endpoint, analytics by_split_type,
and mode switching behaviour.
"""

from datetime import date

from conftest import (
    USER_A, USER_B, USER_A_LOGIN, USER_B_LOGIN,
    PASSWORD_A, PASSWORD_B, make_expense,
)


# ── Helpers ────────────────────────────────────────────────────────────

def _set_mode(auth_client, mode):
    """Switch app mode via the settings API."""
    resp = auth_client.put("/api/settings", json={"app_mode": mode})
    assert resp.status_code == 200
    return resp


# ── Settings API ───────────────────────────────────────────────────────

def test_settings_default_mode(auth_client_a, db):
    """conftest seeds a "shared" Settings row by default (mirroring what
    registering a 2nd user really does). This test instead targets the raw
    resolver fallback for a database that has no Settings row at all — e.g.
    a fresh install, or one seeded directly like this test suite's own
    fixtures — which must be "personal", not "shared"."""
    from sqlalchemy import text
    db.execute(text("DELETE FROM settings"))
    db.commit()

    resp = auth_client_a.get("/api/settings")
    assert resp.status_code == 200
    assert resp.json()["app_mode"] == "personal"


def test_settings_update_mode(auth_client_a):
    for mode in ("personal", "blended", "shared"):
        resp = _set_mode(auth_client_a, mode)
        assert resp.json()["app_mode"] == mode
        # Verify it persists on GET
        assert auth_client_a.get("/api/settings").json()["app_mode"] == mode


def test_settings_invalid_mode_rejected(auth_client_a):
    resp = auth_client_a.put("/api/settings", json={"app_mode": "invalid"})
    assert resp.status_code == 422


def test_settings_empty_mode_rejected(auth_client_a):
    resp = auth_client_a.put("/api/settings", json={"app_mode": ""})
    assert resp.status_code == 422


def test_settings_requires_auth(client):
    resp = client.put("/api/settings", json={"app_mode": "personal"})
    assert resp.status_code == 401


def test_settings_rejects_missing_app_mode(auth_client_a):
    """Pydantic model requires app_mode field (CR-4 / SG-2)."""
    resp = auth_client_a.put("/api/settings", json={})
    assert resp.status_code == 422


def test_settings_rejects_extra_fields_only(auth_client_a):
    """Payload with only extra fields (no app_mode) should fail validation."""
    resp = auth_client_a.put("/api/settings", json={"is_admin": True})
    assert resp.status_code == 422


def test_config_endpoint_includes_mode(auth_client_a):
    """GET /api/config should reflect the current mode."""
    resp = auth_client_a.get("/api/config")
    assert resp.json()["mode"] == "shared"

    _set_mode(auth_client_a, "personal")
    resp = auth_client_a.get("/api/config")
    assert resp.json()["mode"] == "personal"


# ── Personal Mode: Login Restriction ──────────────────────────────────

def test_personal_blocks_user_b_login(auth_client_a, client):
    """A real, registered secondary account gets an honest mode-restriction
    error (403), not the generic "Invalid username or password" (401) —
    see review_order/06-backend-security-access.md #2. Full coverage of this
    behavior (unknown users still get the generic 401, wrong password for
    the primary user still 401s, etc.) lives in test_security_access.py."""
    _set_mode(auth_client_a, "personal")
    resp = client.post("/api/auth/login", json={
        "username": USER_B_LOGIN,
        "password": PASSWORD_B,
    })
    assert resp.status_code == 403


def test_personal_allows_user_a_login(auth_client_a, client):
    _set_mode(auth_client_a, "personal")
    resp = client.post("/api/auth/login", json={
        "username": USER_A_LOGIN,
        "password": PASSWORD_A,
    })
    assert resp.status_code == 200


# ── Personal Mode: Validation ─────────────────────────────────────────

def test_personal_rejects_user_b_as_payer(auth_client_a):
    _set_mode(auth_client_a, "personal")
    resp = auth_client_a.post("/api/expenses", json=make_expense(
        paid_by=USER_B, split_method="Personal",
    ))
    assert resp.status_code == 422
    assert "paid_by" in resp.json()["detail"]


def test_personal_rejects_shared_split(auth_client_a):
    _set_mode(auth_client_a, "personal")
    resp = auth_client_a.post("/api/expenses", json=make_expense(
        split_method="50/50",
    ))
    assert resp.status_code == 422
    assert "split_method" in resp.json()["detail"]


def test_personal_rejects_100_percent_split(auth_client_a):
    _set_mode(auth_client_a, "personal")
    for method in [f"100% {USER_A}", f"100% {USER_B}"]:
        resp = auth_client_a.post("/api/expenses", json=make_expense(
            split_method=method,
        ))
        assert resp.status_code == 422


def test_personal_accepts_personal_expense(auth_client_a):
    _set_mode(auth_client_a, "personal")
    resp = auth_client_a.post("/api/expenses", json=make_expense(
        paid_by=USER_A, split_method="Personal",
    ))
    assert resp.status_code == 201


# ── Personal Mode: Balance ────────────────────────────────────────────

def test_personal_balance_returns_zero(auth_client_a):
    _set_mode(auth_client_a, "personal")
    resp = auth_client_a.get("/api/balance")
    assert resp.status_code == 200
    data = resp.json()
    assert data["amount"] == 0
    assert data["description"] == "Personal mode"


# ── Shared Mode: Validation (existing behaviour preserved) ────────────

def test_shared_accepts_all_split_methods(auth_client_a):
    """Shared mode should accept 50/50, 100% (cross-payer) splits, and Personal."""
    # 50/50 and Personal: payer = Alice (default)
    for method in ["50/50", "Personal"]:
        resp = auth_client_a.post("/api/expenses", json=make_expense(split_method=method))
        assert resp.status_code == 201, f"Failed for split_method={method}"
    # 100% Alice: Bob must be the payer (Bob fronts, Alice owes it all)
    resp = auth_client_a.post("/api/expenses", json=make_expense(
        paid_by=USER_B, split_method=f"100% {USER_A}",
    ))
    assert resp.status_code == 201, "100% Alice paid by Bob should be accepted"
    # 100% Bob: Alice must be the payer (Alice fronts, Bob owes it all)
    resp = auth_client_a.post("/api/expenses", json=make_expense(
        paid_by=USER_A, split_method=f"100% {USER_B}",
    ))
    assert resp.status_code == 201, "100% Bob paid by Alice should be accepted"


def test_shared_rejects_100pct_self(auth_client_a):
    """split_method=100% <payer> is invalid — payer can't owe 100% to themselves."""
    resp = auth_client_a.post("/api/expenses", json=make_expense(
        paid_by=USER_A, split_method=f"100% {USER_A}",
    ))
    assert resp.status_code == 422
    resp = auth_client_a.post("/api/expenses", json=make_expense(
        paid_by=USER_B, split_method=f"100% {USER_B}",
    ))
    assert resp.status_code == 422


def test_shared_accepts_both_payers(auth_client_a):
    for payer in [USER_A, USER_B]:
        resp = auth_client_a.post("/api/expenses", json=make_expense(
            paid_by=payer,
        ))
        assert resp.status_code == 201, f"Failed for paid_by={payer}"


# ── Blended Mode: Validation ──────────────────────────────────────────

def test_blended_accepts_personal_and_shared(auth_client_a):
    _set_mode(auth_client_a, "blended")
    for method in ["50/50", "Personal"]:
        resp = auth_client_a.post("/api/expenses", json=make_expense(split_method=method))
        assert resp.status_code == 201, f"Failed for split_method={method}"
    # 100% Alice requires a cross-payer (Bob fronts, Alice owes)
    resp = auth_client_a.post("/api/expenses", json=make_expense(
        paid_by=USER_B, split_method=f"100% {USER_A}",
    ))
    assert resp.status_code == 201, "100% Alice paid by Bob should be accepted in blended"


def test_blended_accepts_both_payers(auth_client_a):
    _set_mode(auth_client_a, "blended")
    for payer in [USER_A, USER_B]:
        resp = auth_client_a.post("/api/expenses", json=make_expense(
            paid_by=payer,
        ))
        assert resp.status_code == 201, f"Failed for paid_by={payer}"


# ── Personal Summary Endpoint ─────────────────────────────────────────

def test_personal_summary_counts_only_personal(auth_client_a):
    """Only Personal-split expenses paid by the current user this month."""
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=50, split_method="Personal", paid_by=USER_A,
    ))
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=30, split_method="Personal", paid_by=USER_A,
    ))
    # Shared expense — should NOT count
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=200, split_method="50/50", paid_by=USER_A,
    ))
    resp = auth_client_a.get("/api/personal-summary")
    assert resp.status_code == 200
    assert resp.json()["amount"] == 80.0


def test_personal_summary_excludes_other_user(auth_client_a, auth_client_b):
    """User B's personal expenses should not appear in User A's summary."""
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=40, split_method="Personal", paid_by=USER_A,
    ))
    auth_client_b.post("/api/expenses", json=make_expense(
        amount=60, split_method="Personal", paid_by=USER_B,
    ))
    # User A should only see their own
    resp = auth_client_a.get("/api/personal-summary")
    assert resp.json()["amount"] == 40.0


def test_personal_summary_excludes_payment_category(auth_client_a):
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=100, split_method="Personal", paid_by=USER_A, category="Payment",
    ))
    resp = auth_client_a.get("/api/personal-summary")
    assert resp.json()["amount"] == 0.0


def test_personal_summary_nets_reimbursement(auth_client_a):
    """A personal Reimbursement nets into the personal total rather than
    being excluded — see the Reimbursement convention note in CLAUDE.md."""
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=100, split_method="Personal", paid_by=USER_A, category="Groceries",
    ))
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=-20, split_method="Personal", paid_by=USER_A, category="Reimbursement",
    ))
    resp = auth_client_a.get("/api/personal-summary")
    assert resp.json()["amount"] == 80.0


def test_personal_summary_requires_auth(client):
    resp = client.get("/api/personal-summary")
    assert resp.status_code == 401


# ── Analytics: by_split_type ───────────────────────────────────────────

def test_analytics_includes_split_type_breakdown(auth_client_a):
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=100, split_method="50/50",
    ))
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=40, split_method="Personal",
    ))
    resp = auth_client_a.get("/api/analytics")
    assert resp.status_code == 200
    data = resp.json()
    assert "by_split_type" in data
    split_types = {item["type"]: item["amount"] for item in data["by_split_type"]}
    assert split_types["Shared"] == 100.0
    assert split_types["Personal"] == 40.0


# ── Mode Switching: Data Preservation ──────────────────────────────────

def test_mode_switch_preserves_data(auth_client_a):
    """Switching modes should not delete or modify existing expenses."""
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=75, split_method="50/50", description="shared lunch",
    ))
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=25, split_method="Personal", description="coffee",
    ))

    # Switch to personal
    _set_mode(auth_client_a, "personal")
    expenses = auth_client_a.get("/api/expenses").json()
    assert len(expenses) == 2

    # Switch to blended
    _set_mode(auth_client_a, "blended")
    expenses = auth_client_a.get("/api/expenses").json()
    assert len(expenses) == 2
    descriptions = {e["description"] for e in expenses}
    assert descriptions == {"shared lunch", "coffee"}


def test_validation_adapts_after_mode_switch(auth_client_a):
    """After switching to personal, shared splits should be rejected immediately."""
    # Shared: shared split works
    resp = auth_client_a.post("/api/expenses", json=make_expense(
        split_method="50/50",
    ))
    assert resp.status_code == 201

    # Switch to personal: same split should fail
    _set_mode(auth_client_a, "personal")
    resp = auth_client_a.post("/api/expenses", json=make_expense(
        split_method="50/50",
    ))
    assert resp.status_code == 422

    # Switch back to shared: shared split works again
    _set_mode(auth_client_a, "shared")
    resp = auth_client_a.post("/api/expenses", json=make_expense(
        split_method="50/50",
    ))
    assert resp.status_code == 201


def test_personal_edit_allows_historical_shared_split(auth_client_a):
    """A historical 50/50 row created in shared mode must remain editable
    after switching to personal mode — edit validation checks the union of
    every mode's ever-valid values, not just the currently active mode.
    See review_order/07-backend-auditing-editing-hygiene.md #4 (this test
    replaces the old test_personal_edit_rejects_shared_split, which asserted
    the exact bug this fix removes)."""
    # Create in shared mode
    resp = auth_client_a.post("/api/expenses", json=make_expense(
        split_method="50/50",
    ))
    expense_id = resp.json()["id"]

    # Switch to personal — the same historical split must still be editable
    _set_mode(auth_client_a, "personal")
    resp = auth_client_a.put(f"/api/expenses/{expense_id}", json=make_expense(
        split_method="50/50",
    ))
    assert resp.status_code == 200

    # Editing to Personal should also still work
    resp = auth_client_a.put(f"/api/expenses/{expense_id}", json=make_expense(
        paid_by=USER_A, split_method="Personal",
    ))
    assert resp.status_code == 200


def test_personal_edit_allows_historical_paid_by_other_user(auth_client_a):
    """A historical row paid_by the secondary user must remain editable after
    switching to personal mode, even though personal mode's *create* rules
    only allow the primary user as payer."""
    resp = auth_client_a.post("/api/expenses", json=make_expense(
        paid_by=USER_B, split_method="50/50",
    ))
    expense_id = resp.json()["id"]

    _set_mode(auth_client_a, "personal")
    resp = auth_client_a.put(f"/api/expenses/{expense_id}", json=make_expense(
        paid_by=USER_B, split_method="50/50",
    ))
    assert resp.status_code == 200


def test_personal_edit_still_rejects_garbage_split(auth_client_a):
    """The relaxed edit validation widens the *set* of historically-valid
    values — it does not disable validation altogether."""
    resp = auth_client_a.post("/api/expenses", json=make_expense(
        split_method="50/50",
    ))
    expense_id = resp.json()["id"]

    _set_mode(auth_client_a, "personal")
    resp = auth_client_a.put(f"/api/expenses/{expense_id}", json=make_expense(
        split_method="75/25",
    ))
    assert resp.status_code == 422
