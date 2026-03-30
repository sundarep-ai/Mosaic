"""Tests for audit logging on expense mutations."""

import json
from datetime import datetime

from conftest import make_expense


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
