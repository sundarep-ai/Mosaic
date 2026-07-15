"""Tests for audit logging on expense, income, and mode-switch mutations."""

import json
from datetime import datetime

from conftest import make_expense, make_income, set_mode


def _read_entries(audit_log):
    """Read all JSONL entries from the test audit log."""
    if not audit_log.log_path.exists():
        return []
    lines = audit_log.log_path.read_text().strip().split("\n")
    return [json.loads(line) for line in lines if line.strip()]


def test_create_generates_audit_entry(auth_client_a, audit_log):
    auth_client_a.post("/api/expenses", json=make_expense())
    entries = _read_entries(audit_log)
    assert len(entries) == 1
    assert entries[0]["operation"] == "CREATE"
    assert entries[0]["user"] == "alice"
    assert "data" in entries[0]


def test_update_generates_audit_with_before(auth_client_a, audit_log):
    created = auth_client_a.post("/api/expenses", json=make_expense()).json()
    auth_client_a.put(
        f"/api/expenses/{created['id']}",
        json=make_expense(description="Updated"),
    )
    entries = _read_entries(audit_log)
    update_entry = next(e for e in entries if e["operation"] == "UPDATE")
    assert "before" in update_entry
    assert update_entry["before"]["description"] == "Test expense"
    assert update_entry["data"]["description"] == "Updated"


def test_delete_generates_audit_entry(auth_client_a, audit_log):
    created = auth_client_a.post("/api/expenses", json=make_expense()).json()
    auth_client_a.delete(f"/api/expenses/{created['id']}")
    entries = _read_entries(audit_log)
    delete_entry = next(e for e in entries if e["operation"] == "DELETE")
    assert delete_entry["user"] == "alice"
    assert delete_entry["data"]["id"] == created["id"]


def test_merge_generates_audit_entry(auth_client_a, audit_log):
    auth_client_a.post("/api/expenses", json=make_expense(description="A"))
    auth_client_a.post("/api/expenses", json=make_expense(description="B"))
    auth_client_a.post("/api/merge-descriptions", json={
        "merges": [{"target": "A", "sources": ["B"], "category": "Groceries"}],
    })
    entries = _read_entries(audit_log)
    merge_entry = next(e for e in entries if e["operation"] == "MERGE")
    assert merge_entry["data"]["total_updated"] == 1


def test_audit_entry_has_valid_timestamp(auth_client_a, audit_log):
    auth_client_a.post("/api/expenses", json=make_expense())
    entries = _read_entries(audit_log)
    assert "timestamp" in entries[0]
    # Verify it parses as valid ISO datetime
    datetime.fromisoformat(entries[0]["timestamp"])


# ── Income audit logging (07 #1) ───────────────────────────────────────
# Previously income create/update/delete skipped the "every mutation must
# audit" convention entirely — only expenses were covered.


def test_income_create_generates_audit_entry(auth_client_a, audit_log, db):
    set_mode(db, "personal")
    auth_client_a.post("/api/income", json=make_income())
    entries = _read_entries(audit_log)
    assert len(entries) == 1
    assert entries[0]["operation"] == "CREATE"
    assert entries[0]["user"] == "alice"
    assert entries[0]["data"]["source"] == "Salary / Wages"


def test_income_update_generates_audit_with_before(auth_client_a, audit_log, db):
    set_mode(db, "personal")
    created = auth_client_a.post("/api/income", json=make_income(amount=1000)).json()
    auth_client_a.put(f"/api/income/{created['id']}", json=make_income(amount=750))
    entries = _read_entries(audit_log)
    update_entry = next(e for e in entries if e["operation"] == "UPDATE")
    assert update_entry["before"]["amount"] == 1000.0
    assert update_entry["data"]["amount"] == 750.0


def test_income_delete_generates_audit_entry(auth_client_a, audit_log, db):
    set_mode(db, "personal")
    created = auth_client_a.post("/api/income", json=make_income()).json()
    auth_client_a.delete(f"/api/income/{created['id']}")
    entries = _read_entries(audit_log)
    delete_entry = next(e for e in entries if e["operation"] == "DELETE")
    assert delete_entry["user"] == "alice"
    assert delete_entry["data"]["id"] == created["id"]


# ── Mode-switch audit logging (07 #2) ───────────────────────────────────


def test_mode_change_generates_audit_entry(auth_client_a, audit_log):
    auth_client_a.put("/api/settings", json={"app_mode": "personal"})
    entries = _read_entries(audit_log)
    assert len(entries) == 1
    assert entries[0]["operation"] == "MODE_CHANGE"
    assert entries[0]["user"] == "alice"
    assert entries[0]["data"] == {"old_mode": "shared", "new_mode": "personal"}


def test_mode_change_to_same_mode_generates_no_audit_entry(auth_client_a, audit_log):
    """Setting the mode to what it already is is a no-op, not a real switch."""
    auth_client_a.put("/api/settings", json={"app_mode": "shared"})
    assert _read_entries(audit_log) == []
