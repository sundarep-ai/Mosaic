"""
Tests for multi-mode support (solo / duo / hybrid).

Covers: Settings API, mode-aware validation, solo login restriction,
solo balance stub, personal-summary endpoint, analytics by_split_type,
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

def test_settings_default_mode(auth_client_a):
    resp = auth_client_a.get("/api/settings")
    assert resp.status_code == 200
    assert resp.json()["app_mode"] == "duo"


def test_settings_update_mode(auth_client_a):
    for mode in ("solo", "hybrid", "duo"):
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
    resp = client.put("/api/settings", json={"app_mode": "solo"})
    assert resp.status_code == 401


def test_config_endpoint_includes_mode(auth_client_a):
    """GET /api/config should reflect the current mode."""
    resp = auth_client_a.get("/api/config")
    assert resp.json()["mode"] == "duo"

    _set_mode(auth_client_a, "solo")
    resp = auth_client_a.get("/api/config")
    assert resp.json()["mode"] == "solo"


# ── Solo Mode: Login Restriction ───────────────────────────────────────

def test_solo_blocks_user_b_login(auth_client_a, client):
    _set_mode(auth_client_a, "solo")
    resp = client.post("/api/auth/login", json={
        "username": USER_B_LOGIN,
        "password": PASSWORD_B,
    })
    assert resp.status_code == 401


def test_solo_allows_user_a_login(auth_client_a, client):
    _set_mode(auth_client_a, "solo")
    resp = client.post("/api/auth/login", json={
        "username": USER_A_LOGIN,
        "password": PASSWORD_A,
    })
    assert resp.status_code == 200


# ── Solo Mode: Validation ──────────────────────────────────────────────

def test_solo_rejects_user_b_as_payer(auth_client_a):
    _set_mode(auth_client_a, "solo")
    resp = auth_client_a.post("/api/expenses", json=make_expense(
        paid_by=USER_B, split_method="Personal",
    ))
    assert resp.status_code == 422
    assert "paid_by" in resp.json()["detail"]


def test_solo_rejects_shared_split(auth_client_a):
    _set_mode(auth_client_a, "solo")
    resp = auth_client_a.post("/api/expenses", json=make_expense(
        split_method="50/50",
    ))
    assert resp.status_code == 422
    assert "split_method" in resp.json()["detail"]


def test_solo_rejects_100_percent_split(auth_client_a):
    _set_mode(auth_client_a, "solo")
    for method in [f"100% {USER_A}", f"100% {USER_B}"]:
        resp = auth_client_a.post("/api/expenses", json=make_expense(
            split_method=method,
        ))
        assert resp.status_code == 422


def test_solo_accepts_personal_expense(auth_client_a):
    _set_mode(auth_client_a, "solo")
    resp = auth_client_a.post("/api/expenses", json=make_expense(
        paid_by=USER_A, split_method="Personal",
    ))
    assert resp.status_code == 201


# ── Solo Mode: Balance ─────────────────────────────────────────────────

def test_solo_balance_returns_zero(auth_client_a):
    _set_mode(auth_client_a, "solo")
    resp = auth_client_a.get("/api/balance")
    assert resp.status_code == 200
    data = resp.json()
    assert data["amount"] == 0
    assert data["description"] == "Solo mode"


# ── Duo Mode: Validation (existing behaviour preserved) ────────────────

def test_duo_accepts_all_split_methods(auth_client_a):
    """Duo mode should accept 50/50, 100% splits, and Personal."""
    for method in ["50/50", f"100% {USER_A}", f"100% {USER_B}", "Personal"]:
        resp = auth_client_a.post("/api/expenses", json=make_expense(
            split_method=method,
        ))
        assert resp.status_code == 201, f"Failed for split_method={method}"


def test_duo_accepts_both_payers(auth_client_a):
    for payer in [USER_A, USER_B]:
        resp = auth_client_a.post("/api/expenses", json=make_expense(
            paid_by=payer,
        ))
        assert resp.status_code == 201, f"Failed for paid_by={payer}"


# ── Hybrid Mode: Validation ───────────────────────────────────────────

def test_hybrid_accepts_personal_and_shared(auth_client_a):
    _set_mode(auth_client_a, "hybrid")
    for method in ["50/50", f"100% {USER_A}", "Personal"]:
        resp = auth_client_a.post("/api/expenses", json=make_expense(
            split_method=method,
        ))
        assert resp.status_code == 201, f"Failed for split_method={method}"


def test_hybrid_accepts_both_payers(auth_client_a):
    _set_mode(auth_client_a, "hybrid")
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

    # Switch to solo
    _set_mode(auth_client_a, "solo")
    expenses = auth_client_a.get("/api/expenses").json()
    assert len(expenses) == 2

    # Switch to hybrid
    _set_mode(auth_client_a, "hybrid")
    expenses = auth_client_a.get("/api/expenses").json()
    assert len(expenses) == 2
    descriptions = {e["description"] for e in expenses}
    assert descriptions == {"shared lunch", "coffee"}


def test_validation_adapts_after_mode_switch(auth_client_a):
    """After switching to solo, shared splits should be rejected immediately."""
    # Duo: shared split works
    resp = auth_client_a.post("/api/expenses", json=make_expense(
        split_method="50/50",
    ))
    assert resp.status_code == 201

    # Switch to solo: same split should fail
    _set_mode(auth_client_a, "solo")
    resp = auth_client_a.post("/api/expenses", json=make_expense(
        split_method="50/50",
    ))
    assert resp.status_code == 422

    # Switch back to duo: shared split works again
    _set_mode(auth_client_a, "duo")
    resp = auth_client_a.post("/api/expenses", json=make_expense(
        split_method="50/50",
    ))
    assert resp.status_code == 201


def test_solo_edit_rejects_shared_split(auth_client_a):
    """Editing an expense in solo mode must also enforce solo validation."""
    # Create in duo mode
    resp = auth_client_a.post("/api/expenses", json=make_expense(
        split_method="50/50",
    ))
    expense_id = resp.json()["id"]

    # Switch to solo and try to edit with a shared split
    _set_mode(auth_client_a, "solo")
    resp = auth_client_a.put(f"/api/expenses/{expense_id}", json=make_expense(
        split_method="50/50",
    ))
    assert resp.status_code == 422

    # But editing to Personal should work
    resp = auth_client_a.put(f"/api/expenses/{expense_id}", json=make_expense(
        paid_by=USER_A, split_method="Personal",
    ))
    assert resp.status_code == 200
