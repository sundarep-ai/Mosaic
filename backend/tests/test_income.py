"""
Tests for income CRUD, validation, mode restrictions, and analytics.
"""
from datetime import date, timedelta

from conftest import (
    USER_A,
    USER_A_LOGIN,
    USER_B_LOGIN,
    make_expense,
    make_income,
    set_mode,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_solo(auth_client, db):
    set_mode(db, "solo")


def _set_hybrid(auth_client, db):
    set_mode(db, "hybrid")


# ---------------------------------------------------------------------------
# Mode restriction
# ---------------------------------------------------------------------------


def test_add_income_duo_rejected(auth_client_a, db):
    """POST /api/income must return 403 when mode is 'duo' (default)."""
    # Default mode is duo (set in conftest)
    resp = auth_client_a.post("/api/income", json=make_income())
    assert resp.status_code == 403
    assert "Shared mode" in resp.json()["detail"]


def test_list_income_duo_rejected(auth_client_a, db):
    resp = auth_client_a.get("/api/income")
    assert resp.status_code == 403


def test_monthly_summary_duo_rejected(auth_client_a, db):
    resp = auth_client_a.get("/api/income/monthly-summary")
    assert resp.status_code == 403


def test_sankey_duo_rejected(auth_client_a, db):
    resp = auth_client_a.post("/api/income/sankey", json={})
    assert resp.status_code == 403


def test_add_income_solo(auth_client_a, db):
    """POST /api/income succeeds in solo mode."""
    set_mode(db, "solo")
    resp = auth_client_a.post("/api/income", json=make_income())
    assert resp.status_code == 201
    data = resp.json()
    assert data["amount"] == 1000.0
    assert data["source"] == "Salary / Wages"
    assert data["user_id"] == USER_A_LOGIN


def test_add_income_hybrid(auth_client_a, db):
    """POST /api/income succeeds in hybrid mode."""
    set_mode(db, "hybrid")
    resp = auth_client_a.post("/api/income", json=make_income(source="Other"))
    assert resp.status_code == 201
    assert resp.json()["source"] == "Other"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_income_future_date_rejected(auth_client_a, db):
    set_mode(db, "solo")
    future = str(date.today() + timedelta(days=1))
    resp = auth_client_a.post("/api/income", json=make_income(date=future))
    assert resp.status_code == 422


def test_income_negative_amount_rejected(auth_client_a, db):
    set_mode(db, "solo")
    resp = auth_client_a.post("/api/income", json=make_income(amount=-100))
    assert resp.status_code == 422


def test_income_zero_amount_rejected(auth_client_a, db):
    set_mode(db, "solo")
    resp = auth_client_a.post("/api/income", json=make_income(amount=0))
    assert resp.status_code == 422


def test_income_invalid_source_rejected(auth_client_a, db):
    set_mode(db, "solo")
    resp = auth_client_a.post("/api/income", json=make_income(source="Lottery"))
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# CRUD lifecycle
# ---------------------------------------------------------------------------


def test_income_crud(auth_client_a, db):
    set_mode(db, "solo")

    # Create
    created = auth_client_a.post("/api/income", json=make_income(amount=500)).json()
    assert created["amount"] == 500.0
    income_id = created["id"]

    # Read via list
    listed = auth_client_a.get("/api/income").json()
    assert any(e["id"] == income_id for e in listed)

    # Update
    updated = auth_client_a.put(
        f"/api/income/{income_id}",
        json=make_income(amount=750, source="Freelance / Side Income"),
    ).json()
    assert updated["amount"] == 750.0
    assert updated["source"] == "Freelance / Side Income"

    # Delete
    resp = auth_client_a.delete(f"/api/income/{income_id}")
    assert resp.status_code == 204

    # Gone
    listed_after = auth_client_a.get("/api/income").json()
    assert not any(e["id"] == income_id for e in listed_after)


def test_income_update_not_found(auth_client_a, db):
    set_mode(db, "solo")
    resp = auth_client_a.put("/api/income/99999", json=make_income())
    assert resp.status_code == 404


def test_income_delete_not_found(auth_client_a, db):
    set_mode(db, "solo")
    resp = auth_client_a.delete("/api/income/99999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Per-user isolation
# ---------------------------------------------------------------------------


def test_income_user_isolation(auth_client_a, auth_client_b, db):
    """User A's income must not appear in User B's listing."""
    set_mode(db, "hybrid")

    auth_client_a.post("/api/income", json=make_income(amount=2000))

    resp_b = auth_client_b.get("/api/income")
    assert resp_b.status_code == 200
    assert len(resp_b.json()) == 0


def test_income_owner_can_edit(auth_client_a, db):
    set_mode(db, "solo")
    created = auth_client_a.post("/api/income", json=make_income()).json()
    resp = auth_client_a.put(f"/api/income/{created['id']}", json=make_income(amount=999))
    assert resp.status_code == 200


def test_income_other_user_cannot_edit(auth_client_a, auth_client_b, db):
    set_mode(db, "hybrid")
    created = auth_client_a.post("/api/income", json=make_income()).json()
    resp = auth_client_b.put(f"/api/income/{created['id']}", json=make_income(amount=1))
    assert resp.status_code == 403


def test_income_other_user_cannot_delete(auth_client_a, auth_client_b, db):
    set_mode(db, "hybrid")
    created = auth_client_a.post("/api/income", json=make_income()).json()
    resp = auth_client_b.delete(f"/api/income/{created['id']}")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Monthly summary
# ---------------------------------------------------------------------------


def test_income_monthly_summary_empty(auth_client_a, db):
    set_mode(db, "solo")
    resp = auth_client_a.get("/api/income/monthly-summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0.0
    assert data["by_source"] == []


def test_income_monthly_summary(auth_client_a, db):
    set_mode(db, "solo")
    auth_client_a.post("/api/income", json=make_income(amount=3000, source="Salary / Wages"))
    auth_client_a.post("/api/income", json=make_income(amount=500, source="Freelance / Side Income"))

    resp = auth_client_a.get("/api/income/monthly-summary")
    assert resp.status_code == 200
    data = resp.json()
    assert abs(data["total"] - 3500.0) < 0.01
    sources = {s["source"]: s["amount"] for s in data["by_source"]}
    assert abs(sources["Salary / Wages"] - 3000.0) < 0.01
    assert abs(sources["Freelance / Side Income"] - 500.0) < 0.01


def test_monthly_summary_excludes_past_months(auth_client_a, db):
    set_mode(db, "solo")
    last_month = str(date.today().replace(day=1) - timedelta(days=1))
    auth_client_a.post("/api/income", json=make_income(amount=9999, date=last_month))

    resp = auth_client_a.get("/api/income/monthly-summary")
    data = resp.json()
    assert data["total"] == 0.0


# ---------------------------------------------------------------------------
# Sankey data
# ---------------------------------------------------------------------------


def test_income_sankey_empty(auth_client_a, db):
    """Sankey with no income returns all zeros."""
    set_mode(db, "solo")
    resp = auth_client_a.post("/api/income/sankey", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["income_total"] == 0.0
    assert data["expenses_total"] == 0.0
    assert data["savings"] == 0.0
    assert data["by_source"] == []
    assert data["by_category"] == []


def test_income_sankey_with_savings(auth_client_a, db):
    """Savings = income - expenses when income > expenses."""
    set_mode(db, "solo")

    # Add income
    auth_client_a.post("/api/income", json=make_income(amount=5000, source="Salary / Wages"))

    # Add expense (Personal, paid by Alice — 100% hers in solo)
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(
            amount=2000,
            category="Rent",
            paid_by=USER_A,
            split_method="Personal",
        ),
    )

    resp = auth_client_a.post("/api/income/sankey", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert abs(data["income_total"] - 5000.0) < 0.01
    assert abs(data["expenses_total"] - 2000.0) < 0.01
    assert abs(data["savings"] - 3000.0) < 0.01
    assert any(s["source"] == "Salary / Wages" for s in data["by_source"])
    assert any(c["category"] == "Rent" for c in data["by_category"])


def test_income_sankey_no_savings_when_expenses_exceed_income(auth_client_a, db):
    """Savings should be 0 when expenses exceed income."""
    set_mode(db, "solo")

    auth_client_a.post("/api/income", json=make_income(amount=500))
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(amount=1000, split_method="Personal", paid_by=USER_A),
    )

    data = auth_client_a.post("/api/income/sankey", json={}).json()
    assert data["savings"] == 0.0


def test_income_sankey_excludes_payment_category(auth_client_a, db):
    """Payment and Reimbursement categories must be excluded from sankey expenses."""
    set_mode(db, "solo")
    auth_client_a.post("/api/income", json=make_income(amount=1000))
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(amount=200, category="Payment", split_method="Personal", paid_by=USER_A),
    )
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(amount=300, category="Groceries", split_method="Personal", paid_by=USER_A),
    )

    data = auth_client_a.post("/api/income/sankey", json={}).json()
    categories = [c["category"] for c in data["by_category"]]
    assert "Payment" not in categories
    assert "Groceries" in categories
    # Only Groceries counted in expenses
    assert abs(data["expenses_total"] - 300.0) < 0.01


def test_income_sankey_date_filter(auth_client_a, db):
    """Date range filter restricts both income and expenses."""
    set_mode(db, "solo")
    today = str(date.today())
    last_month = str(date.today().replace(day=1) - timedelta(days=1))

    auth_client_a.post("/api/income", json=make_income(amount=1000, date=today))
    auth_client_a.post("/api/income", json=make_income(amount=9999, date=last_month))

    data = auth_client_a.post(
        "/api/income/sankey",
        json={"start_date": today, "end_date": today},
    ).json()
    assert abs(data["income_total"] - 1000.0) < 0.01


# ---------------------------------------------------------------------------
# Sankey Pydantic validation (CR-6 / SG-2)
# ---------------------------------------------------------------------------


def test_income_sankey_malformed_date_rejected(auth_client_a, db):
    """Malformed date strings should return 422, not 500 (CR-6)."""
    set_mode(db, "solo")
    resp = auth_client_a.post("/api/income/sankey", json={
        "start_date": "not-a-date",
    })
    assert resp.status_code == 422


def test_income_sankey_partial_dates_ok(auth_client_a, db):
    """Omitting one date should work fine."""
    set_mode(db, "solo")
    today = str(date.today())
    resp = auth_client_a.post("/api/income/sankey", json={"start_date": today})
    assert resp.status_code == 200


def test_income_notes_max_length_rejected(auth_client_a, db):
    """Notes exceeding 500 characters should be rejected (WR-4)."""
    set_mode(db, "solo")
    long_notes = "x" * 501
    resp = auth_client_a.post("/api/income", json=make_income(notes=long_notes))
    assert resp.status_code == 422


def test_income_notes_max_length_accepted(auth_client_a, db):
    """Notes of exactly 500 characters should be accepted."""
    set_mode(db, "solo")
    notes = "x" * 500
    resp = auth_client_a.post("/api/income", json=make_income(notes=notes))
    assert resp.status_code == 201
