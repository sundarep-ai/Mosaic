"""Tests for expense CRUD, validation, authorization, and filtering."""

from datetime import date, timedelta
from decimal import Decimal

from conftest import make_expense, USER_A, USER_B, USER_A_LOGIN
from models import Expense


# ── CRUD ────────────────────────────────────────────────────────────


def test_create_expense(auth_client_a):
    resp = auth_client_a.post("/api/expenses", json=make_expense())
    assert resp.status_code == 201
    data = resp.json()
    assert data["description"] == "Test expense"
    assert data["amount"] == 100.0
    assert data["category"] == "Groceries"
    assert data["user_id"] == USER_A_LOGIN


def test_get_expense(auth_client_a):
    created = auth_client_a.post("/api/expenses", json=make_expense()).json()
    resp = auth_client_a.get(f"/api/expenses/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_nonexistent_expense(auth_client_a):
    assert auth_client_a.get("/api/expenses/99999").status_code == 404


def test_list_expenses(auth_client_a):
    auth_client_a.post("/api/expenses", json=make_expense(description="First"))
    auth_client_a.post("/api/expenses", json=make_expense(description="Second"))
    resp = auth_client_a.get("/api/expenses")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_update_expense(auth_client_a):
    created = auth_client_a.post("/api/expenses", json=make_expense()).json()
    updated_payload = make_expense(description="Updated", amount=200.0)
    resp = auth_client_a.put(f"/api/expenses/{created['id']}", json=updated_payload)
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated"
    assert resp.json()["amount"] == 200.0


def test_delete_expense(auth_client_a):
    created = auth_client_a.post("/api/expenses", json=make_expense()).json()
    resp = auth_client_a.delete(f"/api/expenses/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert auth_client_a.get(f"/api/expenses/{created['id']}").status_code == 404


# ── Authorization ───────────────────────────────────────────────────


def test_either_user_can_update_the_others_expense(auth_client_a, auth_client_b):
    """Two trusted partners can fix a typo in each other's entries — the audit
    trail (not an ownership lock) is the accountability mechanism. See
    review_order/07-backend-auditing-editing-hygiene.md #3."""
    created = auth_client_a.post("/api/expenses", json=make_expense()).json()
    resp = auth_client_b.put(
        f"/api/expenses/{created['id']}", json=make_expense(description="Fixed typo")
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "Fixed typo"


def test_editing_does_not_transfer_ownership(auth_client_a, auth_client_b):
    """Bob editing Alice's expense must not silently reassign it to Bob — that
    would lock Alice out of editing it back afterward."""
    created = auth_client_a.post("/api/expenses", json=make_expense()).json()
    assert created["user_id"] == USER_A_LOGIN

    auth_client_b.put(
        f"/api/expenses/{created['id']}", json=make_expense(description="Edited by Bob")
    )
    resp = auth_client_a.get(f"/api/expenses/{created['id']}")
    assert resp.json()["user_id"] == USER_A_LOGIN

    # Alice must still be able to edit it back after Bob's edit.
    resp = auth_client_a.put(
        f"/api/expenses/{created['id']}", json=make_expense(description="Edited by Alice again")
    )
    assert resp.status_code == 200


def test_cannot_delete_other_users_expense(auth_client_a, auth_client_b):
    created = auth_client_a.post("/api/expenses", json=make_expense()).json()
    resp = auth_client_b.delete(f"/api/expenses/{created['id']}")
    assert resp.status_code == 403


def test_can_update_legacy_expense(auth_client_b, db):
    expense = Expense(
        date=date.today(), description="Legacy", amount=Decimal("50.00"),
        category="Groceries", paid_by=USER_A, split_method="50/50", user_id=None,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)

    resp = auth_client_b.put(
        f"/api/expenses/{expense.id}", json=make_expense(description="Updated legacy")
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated legacy"
    # Editing a legacy (ownerless) row must not assign it an owner either.
    assert resp.json()["user_id"] is None


def test_can_delete_legacy_expense(auth_client_b, db):
    expense = Expense(
        date=date.today(), description="Legacy", amount=Decimal("50.00"),
        category="Groceries", paid_by=USER_A, split_method="50/50", user_id=None,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)

    resp = auth_client_b.delete(f"/api/expenses/{expense.id}")
    assert resp.status_code == 200


# ── Validation ──────────────────────────────────────────────────────


def test_reject_zero_amount(auth_client_a):
    resp = auth_client_a.post("/api/expenses", json=make_expense(amount=0))
    assert resp.status_code == 422


def test_reject_future_date(auth_client_a):
    future = str(date.today() + timedelta(days=1))
    resp = auth_client_a.post("/api/expenses", json=make_expense(date=future))
    assert resp.status_code == 422


def test_reject_negative_non_reimbursement(auth_client_a):
    resp = auth_client_a.post(
        "/api/expenses", json=make_expense(amount=-50, category="Groceries")
    )
    assert resp.status_code == 422


def test_allow_negative_reimbursement(auth_client_a):
    resp = auth_client_a.post(
        "/api/expenses", json=make_expense(amount=-50, category="Reimbursement")
    )
    assert resp.status_code == 201


def test_reject_invalid_paid_by(auth_client_a):
    resp = auth_client_a.post("/api/expenses", json=make_expense(paid_by="Unknown"))
    assert resp.status_code == 422


def test_reject_invalid_split_method(auth_client_a):
    resp = auth_client_a.post("/api/expenses", json=make_expense(split_method="75/25"))
    assert resp.status_code == 422


def test_amount_rounded_to_2_decimals(auth_client_a):
    resp = auth_client_a.post("/api/expenses", json=make_expense(amount=99.999))
    assert resp.status_code == 201
    assert resp.json()["amount"] == 100.0


# ── Filtering & Sorting ────────────────────────────────────────────


def test_filter_by_paid_by(auth_client_a):
    auth_client_a.post("/api/expenses", json=make_expense(paid_by=USER_A))
    auth_client_a.post("/api/expenses", json=make_expense(paid_by=USER_B))
    resp = auth_client_a.get(f"/api/expenses?paid_by={USER_A}")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["paid_by"] == USER_A


def test_filter_by_category(auth_client_a):
    auth_client_a.post("/api/expenses", json=make_expense(category="Groceries"))
    auth_client_a.post("/api/expenses", json=make_expense(category="Dining"))
    resp = auth_client_a.get("/api/expenses?category=Dining")
    assert len(resp.json()) == 1
    assert resp.json()[0]["category"] == "Dining"


def test_filter_by_date_range(auth_client_a):
    today = date.today()
    yesterday = today - timedelta(days=1)
    auth_client_a.post("/api/expenses", json=make_expense(date=str(today)))
    auth_client_a.post("/api/expenses", json=make_expense(date=str(yesterday)))
    resp = auth_client_a.get(f"/api/expenses?start_date={today}&end_date={today}")
    assert len(resp.json()) == 1


def test_sort_by_amount_asc(auth_client_a):
    auth_client_a.post("/api/expenses", json=make_expense(amount=50))
    auth_client_a.post("/api/expenses", json=make_expense(amount=200))
    auth_client_a.post("/api/expenses", json=make_expense(amount=100))
    resp = auth_client_a.get("/api/expenses?sort_by=amount&sort=asc")
    amounts = [e["amount"] for e in resp.json()]
    assert amounts == [50.0, 100.0, 200.0]


def test_sort_by_date_desc_is_default(auth_client_a):
    today = date.today()
    yesterday = today - timedelta(days=1)
    auth_client_a.post("/api/expenses", json=make_expense(date=str(yesterday), description="Old"))
    auth_client_a.post("/api/expenses", json=make_expense(date=str(today), description="New"))
    resp = auth_client_a.get("/api/expenses")
    descriptions = [e["description"] for e in resp.json()]
    assert descriptions[0] == "New"
    assert descriptions[1] == "Old"


def test_limit(auth_client_a):
    for i in range(5):
        auth_client_a.post("/api/expenses", json=make_expense(description=f"Expense {i}"))
    resp = auth_client_a.get("/api/expenses?limit=3")
    assert len(resp.json()) == 3


def test_search(auth_client_a):
    auth_client_a.post("/api/expenses", json=make_expense(description="Walmart groceries"))
    auth_client_a.post("/api/expenses", json=make_expense(description="Restaurant dinner"))
    resp = auth_client_a.get("/api/expenses?search=Walmart")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["description"] == "Walmart groceries"


# ── Category Validation (WR-3) ───────────────────────────────────────


def test_accept_custom_category(auth_client_a):
    """A novel category name must be accepted, not rejected."""
    resp = auth_client_a.post("/api/expenses", json=make_expense(category="Home Renovation"))
    assert resp.status_code == 201
    assert resp.json()["category"] == "Home Renovation"


def test_reject_empty_category(auth_client_a):
    resp = auth_client_a.post("/api/expenses", json=make_expense(category=""))
    assert resp.status_code == 422


def test_reject_whitespace_only_category(auth_client_a):
    resp = auth_client_a.post("/api/expenses", json=make_expense(category="   "))
    assert resp.status_code == 422


def test_reject_reserved_category_lookalike(auth_client_a):
    """A custom category that only differs by case from a reserved category
    (e.g. Payment/Reimbursement) must be rejected, not silently inherit that
    reserved category's money-math semantics."""
    resp = auth_client_a.post("/api/expenses", json=make_expense(category="payment"))
    assert resp.status_code == 422
    assert "Payment" in resp.json()["detail"]


def test_reject_case_collision_with_standard_category(auth_client_a):
    """A custom category differing only by case from a standard category must
    be rejected, so analytics don't fragment 'groceries' from 'Groceries'."""
    resp = auth_client_a.post("/api/expenses", json=make_expense(category="groceries"))
    assert resp.status_code == 422
    assert "Groceries" in resp.json()["detail"]


def test_custom_category_stored_trimmed(auth_client_a):
    resp = auth_client_a.post("/api/expenses", json=make_expense(category="  Side Hustle  "))
    assert resp.status_code == 201
    assert resp.json()["category"] == "Side Hustle"


def test_accept_all_standard_categories(auth_client_a):
    """All standard categories must be accepted."""
    for cat in ["Groceries", "Rent", "Dining", "Reimbursement", "Payment"]:
        resp = auth_client_a.post("/api/expenses", json=make_expense(
            category=cat,
            amount=-10 if cat == "Reimbursement" else 10,
            # Payment only means "settle the balance in full" — it must use a
            # 100% split, unlike every other category which defaults to 50/50.
            split_method=f"100% {USER_B}" if cat == "Payment" else "50/50",
        ))
        assert resp.status_code == 201, f"Failed for category={cat}"


# ── Payment split enforcement (B1 #1) ──────────────────────────────────


def test_payment_rejects_50_50_split(auth_client_a):
    """A Payment can only mean 'settle in full' — a 50/50 split moves the
    balance by half the settlement, silently corrupting it forever."""
    resp = auth_client_a.post("/api/expenses", json=make_expense(
        category="Payment", amount=50, split_method="50/50",
    ))
    assert resp.status_code == 422
    assert "100%" in resp.json()["detail"]


def test_payment_rejects_personal_split(auth_client_a):
    resp = auth_client_a.post("/api/expenses", json=make_expense(
        category="Payment", amount=50, split_method="Personal",
    ))
    assert resp.status_code == 422


def test_payment_accepts_100_percent_split(auth_client_a):
    resp = auth_client_a.post("/api/expenses", json=make_expense(
        category="Payment", amount=50, paid_by=USER_A, split_method=f"100% {USER_B}",
    ))
    assert resp.status_code == 201


def test_payment_still_rejects_100_percent_self(auth_client_a):
    """Existing rule (100% to payer themselves is meaningless) still applies to Payment."""
    resp = auth_client_a.post("/api/expenses", json=make_expense(
        category="Payment", amount=50, paid_by=USER_A, split_method=f"100% {USER_A}",
    ))
    assert resp.status_code == 422


def test_payment_update_rejects_50_50_split(auth_client_a):
    """The same enforcement applies on edit, not just create."""
    created = auth_client_a.post("/api/expenses", json=make_expense(
        category="Payment", amount=50, paid_by=USER_A, split_method=f"100% {USER_B}",
    )).json()
    resp = auth_client_a.put(f"/api/expenses/{created['id']}", json=make_expense(
        category="Payment", amount=50, paid_by=USER_A, split_method="50/50",
    ))
    assert resp.status_code == 422


# ── Field Length Validation (WR-4) ────────────────────────────────────


def test_reject_too_long_description(auth_client_a):
    """Description exceeding 500 characters must be rejected."""
    long_desc = "x" * 501
    resp = auth_client_a.post("/api/expenses", json=make_expense(description=long_desc))
    assert resp.status_code == 422


def test_accept_max_length_description(auth_client_a):
    """Description of exactly 500 characters must be accepted."""
    desc = "x" * 500
    resp = auth_client_a.post("/api/expenses", json=make_expense(description=desc))
    assert resp.status_code == 201


def test_reject_too_long_category(auth_client_a):
    """Category exceeding 100 characters must be rejected."""
    long_cat = "x" * 101
    resp = auth_client_a.post("/api/expenses", json=make_expense(category=long_cat))
    assert resp.status_code == 422


# ── Merge Descriptions Pydantic Validation (CR-5 / SG-2) ─────────────


def test_merge_descriptions_valid(auth_client_a):
    """Valid merge payload with Pydantic model. Asserts the actual updated
    count and that every merged row's description really changed — `updated
    >= 0` is a tautology that passes even if nothing was touched at all."""
    auth_client_a.post("/api/expenses", json=make_expense(description="Costco run"))
    auth_client_a.post("/api/expenses", json=make_expense(description="Costco trip"))
    # A same-category, non-matching description must be left alone.
    auth_client_a.post("/api/expenses", json=make_expense(description="Walmart"))

    resp = auth_client_a.post("/api/merge-descriptions", json={
        "merges": [{"target": "Costco", "sources": ["Costco run", "Costco trip"], "category": "Groceries"}]
    })
    assert resp.status_code == 200
    assert resp.json()["updated"] == 2

    descriptions = sorted(e["description"] for e in auth_client_a.get("/api/expenses").json())
    assert descriptions == ["Costco", "Costco", "Walmart"]


def test_merge_descriptions_missing_fields(auth_client_a):
    """Missing required fields should return 422 (Pydantic validation)."""
    resp = auth_client_a.post("/api/merge-descriptions", json={})
    assert resp.status_code == 422


def test_merge_descriptions_bad_type(auth_client_a):
    """Sources must be a list of strings."""
    resp = auth_client_a.post("/api/merge-descriptions", json={
        "merges": [{"target": "X", "sources": 123, "category": "Groceries"}]
    })
    assert resp.status_code == 422
