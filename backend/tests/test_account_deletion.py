"""Tests for account deletion — audit trail, embedded display-name cleanup on the
survivor's rows, and ownership reassignment (bucket 05, item 1).
"""

import json

import pytest
from sqlmodel import select

from conftest import USER_A, USER_B, USER_A_LOGIN, USER_B_LOGIN, PASSWORD_B, make_expense, set_mode
from config import get_app_mode
from models import Expense, User
from users import get_user_by_username


def _read_entries(audit_log):
    if not audit_log.log_path.exists():
        return []
    lines = audit_log.log_path.read_text().strip().split("\n")
    return [json.loads(line) for line in lines if line.strip()]


def _delete_account(client, password=PASSWORD_B, data_action="delete"):
    return client.request(
        "DELETE",
        "/api/auth/account",
        json={"password": password, "data_action": data_action},
    )


# ── Audit trail ───────────────────────────────────────────────────────────────


def test_delete_account_generates_audit_entry_with_scope(auth_client_b, audit_log):
    resp = auth_client_b.post("/api/expenses", json=make_expense(paid_by=USER_B, split_method="50/50"))
    assert resp.status_code == 201

    resp = _delete_account(auth_client_b, data_action="delete")
    assert resp.status_code == 200

    entries = _read_entries(audit_log)
    account_delete_entries = [e for e in entries if e["operation"] == "ACCOUNT_DELETE"]
    assert len(account_delete_entries) == 1
    entry = account_delete_entries[0]
    assert entry["user"] == USER_B_LOGIN
    assert entry["data"]["data_action"] == "delete"
    assert entry["data"]["deleted_username"] == USER_B_LOGIN
    assert entry["data"]["deleted_display_name"] == USER_B
    assert entry["data"]["expenses_deleted"] == 1


def test_response_surfaces_deletion_scope_counts(auth_client_b):
    auth_client_b.post("/api/expenses", json=make_expense(paid_by=USER_B, split_method="50/50"))
    resp = _delete_account(auth_client_b, data_action="delete")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["expenses_deleted"] == 1
    assert data["data_action"] == "delete"


# ── Delete action ─────────────────────────────────────────────────────────────


def test_delete_action_removes_expenses_paid_by_departing_user(auth_client_b, db):
    auth_client_b.post("/api/expenses", json=make_expense(paid_by=USER_B, split_method="50/50"))
    _delete_account(auth_client_b, data_action="delete")
    remaining = db.exec(select(Expense)).all()
    assert remaining == []


def test_delete_action_reassigns_user_id_on_survivor_paid_rows(auth_client_a, auth_client_b, db):
    # Bob records an expense that Alice actually paid for.
    created = auth_client_b.post(
        "/api/expenses",
        json=make_expense(paid_by=USER_A, split_method="50/50"),
    ).json()
    assert created["paid_by"] == USER_A

    _delete_account(auth_client_b, data_action="delete")

    expense = db.get(Expense, created["id"])
    assert expense is not None  # paid_by == survivor, so not deleted
    assert expense.user_id == USER_A_LOGIN

    # Alice must now be able to edit her own history instead of being locked out
    # by the ownership check because it still referenced Bob's login. Deleting
    # the second user forces app_mode back to "personal", where the only valid
    # split_method is "Personal" — that's what a real solo-mode edit would send.
    edit_resp = auth_client_a.put(
        f"/api/expenses/{created['id']}",
        json=make_expense(paid_by=USER_A, split_method="Personal", description="Edited"),
    )
    assert edit_resp.status_code == 200


def test_delete_action_folds_debt_owed_by_departing_user_into_survivors_personal_spend(
    auth_client_a, auth_client_b, db
):
    # Alice paid, but the split assigns the full amount to Bob (Bob owed her in full).
    created = auth_client_a.post(
        "/api/expenses",
        json=make_expense(paid_by=USER_A, split_method=f"100% {USER_B}"),
    ).json()

    _delete_account(auth_client_b, data_action="delete")

    expense = db.get(Expense, created["id"])
    assert expense is not None
    assert expense.split_method == "Personal"
    assert expense.paid_by == USER_A


# ── Anonymize action ──────────────────────────────────────────────────────────


def test_anonymize_action_sets_paid_by_to_deleted_user(auth_client_b, db):
    created = auth_client_b.post(
        "/api/expenses", json=make_expense(paid_by=USER_B, split_method="50/50")
    ).json()
    _delete_account(auth_client_b, data_action="anonymize")

    expense = db.get(Expense, created["id"])
    assert expense is not None
    assert expense.paid_by == "Deleted User"
    assert expense.split_method == "50/50"  # unaffected — no name embedded in "50/50"


def test_anonymize_action_folds_debt_owed_by_departing_user_into_survivors_personal_spend(
    auth_client_a, auth_client_b, db
):
    created = auth_client_a.post(
        "/api/expenses",
        json=make_expense(paid_by=USER_A, split_method=f"100% {USER_B}"),
    ).json()

    _delete_account(auth_client_b, data_action="anonymize")

    expense = db.get(Expense, created["id"])
    assert expense is not None
    assert expense.split_method == "Personal"
    assert expense.paid_by == USER_A  # survivor's own paid_by is untouched


def test_anonymize_action_reassigns_user_id_on_survivor_paid_rows(auth_client_a, auth_client_b, db):
    created = auth_client_b.post(
        "/api/expenses",
        json=make_expense(paid_by=USER_A, split_method="50/50"),
    ).json()

    _delete_account(auth_client_b, data_action="anonymize")

    expense = db.get(Expense, created["id"])
    assert expense.user_id == USER_A_LOGIN


# ── App mode still forced to personal afterward ──────────────────────────────


def test_deletion_forces_personal_mode_with_one_user_remaining(auth_client_b, db):
    # conftest already seeds a "shared" Settings row (mirroring real 2nd-user
    # registration) — set_mode() here just makes that starting point explicit
    # rather than relying on the fixture default. Reads the mode through
    # get_app_mode() (the same resolver every route uses) rather than a raw
    # db.get(Settings, 1), which is exactly what the no-row variant below
    # needs to hit `None` on and would prove nothing either way here.
    set_mode(db, "shared")

    _delete_account(auth_client_b, data_action="delete")
    assert get_app_mode(db) == "personal"
    assert db.exec(select(User)).all() != []  # Alice still exists


def test_deletion_forces_personal_mode_with_no_settings_row(auth_client_b, db):
    """Same regression, but for the common case where Settings has never
    been written at all (a fresh install that never explicitly switched
    modes) — deletion must not crash trying to update a nonexistent row."""
    from sqlalchemy import text
    db.execute(text("DELETE FROM settings"))
    db.commit()

    _delete_account(auth_client_b, data_action="delete")
    assert get_app_mode(db) == "personal"


# ── Survivor's balance/analytics after deletion (bucket 08, item 4) ──────────
# The tests above assert the mutation's own correctness (rows, audit, scope).
# These assert what the survivor actually *sees* afterward on the endpoints
# that read that data back — the whole point of the folding/reassignment
# logic above is to keep those numbers correct, not just avoid a crash.


def test_delete_survivor_balance_and_analytics_reflect_folded_debt(auth_client_a, auth_client_b, db):
    """Alice paid $100 that was entirely Bob's share (100% Bob) — Bob owed
    her in full. After deleting Bob, that debt is uncollectable and folds
    into Alice's own Personal spend (see the fold-in logic in auth.py)."""
    set_mode(db, "shared")
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(paid_by=USER_A, split_method=f"100% {USER_B}", amount=100),
    )

    _delete_account(auth_client_b, data_action="delete")

    # Deletion forces the app back to personal mode, so /api/balance reports
    # the personal-mode stub rather than crashing on a missing 2nd user.
    balance = auth_client_a.get("/api/balance").json()
    assert balance == {"amount": 0, "description": "Personal mode"}

    my_expense = auth_client_a.get("/api/my-expense-summary").json()
    assert my_expense["my_total"] == 100.0

    analytics = auth_client_a.get("/api/analytics").json()
    assert analytics["total_spend"] == 100.0


def test_anonymize_survivor_balance_and_analytics_reflect_folded_debt(auth_client_a, auth_client_b, db):
    """Same scenario as the delete-action version above, but for anonymize —
    the fold-in logic runs identically for both data_actions."""
    set_mode(db, "shared")
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(paid_by=USER_A, split_method=f"100% {USER_B}", amount=100),
    )

    _delete_account(auth_client_b, data_action="anonymize")

    balance = auth_client_a.get("/api/balance").json()
    assert balance == {"amount": 0, "description": "Personal mode"}

    my_expense = auth_client_a.get("/api/my-expense-summary").json()
    assert my_expense["my_total"] == 100.0

    analytics = auth_client_a.get("/api/analytics").json()
    assert analytics["total_spend"] == 100.0


def test_delete_survivor_true_50_50_share_is_preserved_not_zeroed(auth_client_a, auth_client_b, db):
    """A genuine 50/50 joint expense Alice paid is intentionally NOT folded
    into Personal (unlike the "100% departing user" case) — her own 50%
    share is unaffected by Bob's departure and must keep showing as exactly
    that share, neither zeroed out nor doubled up to the full amount."""
    set_mode(db, "shared")
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(paid_by=USER_A, split_method="50/50", amount=100),
    )

    _delete_account(auth_client_b, data_action="delete")

    my_expense = auth_client_a.get("/api/my-expense-summary").json()
    assert my_expense["my_total"] == 50.0

    monthly_summary = auth_client_a.get("/api/monthly-summary").json()
    assert sum(item["amount"] for item in monthly_summary) == 50.0


def test_anonymize_survivor_true_50_50_share_is_preserved_when_departing_user_paid(
    auth_client_a, auth_client_b, db
):
    """A 50/50 expense Bob actually paid for: anonymizing repoints paid_by
    to "Deleted User" but must not touch the split — Alice's own 50% share
    (the _my_portion_expr "50/50" branch doesn't look at paid_by at all)
    must be unaffected."""
    set_mode(db, "shared")
    auth_client_b.post(
        "/api/expenses",
        json=make_expense(paid_by=USER_B, split_method="50/50", amount=80),
    )

    _delete_account(auth_client_b, data_action="anonymize")

    my_expense = auth_client_a.get("/api/my-expense-summary").json()
    assert my_expense["my_total"] == 40.0


def test_delete_in_blended_mode_still_forces_personal_and_zeros_balance(auth_client_a, auth_client_b, db):
    """Deletion's mode-forcing (and the balance endpoint's personal-mode
    short-circuit) must hold regardless of which multi-user mode the app
    was in beforehand — not just "shared"."""
    set_mode(db, "blended")
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(paid_by=USER_A, split_method="50/50", amount=60),
    )

    _delete_account(auth_client_b, data_action="delete")

    assert get_app_mode(db) == "personal"
    balance = auth_client_a.get("/api/balance").json()
    assert balance == {"amount": 0, "description": "Personal mode"}


# ── Avatar deletion ordering (bucket 06, item 4) ──────────────────────────────
# The avatar file must only be removed after the DB commit succeeds — otherwise
# a commit failure leaves the account intact but the avatar file gone.


def test_avatar_removed_after_successful_deletion(auth_client_b, db, monkeypatch, tmp_path):
    import auth as auth_mod

    avatar_path = tmp_path / "bob.png"
    avatar_path.write_bytes(b"\x89PNG fake avatar")
    monkeypatch.setattr(
        auth_mod, "_find_avatar",
        lambda username: str(avatar_path) if username == USER_B_LOGIN else None,
    )

    resp = _delete_account(auth_client_b, data_action="delete")
    assert resp.status_code == 200
    assert not avatar_path.exists()


def test_avatar_file_untouched_until_commit_succeeds(auth_client_b, db, monkeypatch, tmp_path):
    """Regression test for the delete-before-commit ordering bug: force the
    avatar removal itself to fail, and confirm the DB commit already went
    through beforehand (proving removal now happens strictly after commit,
    not before it)."""
    import auth as auth_mod

    avatar_path = tmp_path / "bob.png"
    avatar_path.write_bytes(b"\x89PNG fake avatar")
    monkeypatch.setattr(
        auth_mod, "_find_avatar",
        lambda username: str(avatar_path) if username == USER_B_LOGIN else None,
    )

    def _boom(path):
        raise OSError("simulated failure removing avatar file")

    monkeypatch.setattr(auth_mod.os, "remove", _boom)

    with pytest.raises(OSError):
        _delete_account(auth_client_b, data_action="delete")

    # The account row is already gone even though the (post-commit) avatar
    # removal blew up — proving the commit happened first.
    assert get_user_by_username(db, USER_B_LOGIN) is None
    # And the file itself was never actually deleted, since os.remove was
    # mocked to raise instead of delete.
    assert avatar_path.exists()
