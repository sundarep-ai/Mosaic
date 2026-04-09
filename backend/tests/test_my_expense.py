"""Tests for the my-expense-summary endpoint."""

from datetime import date, timedelta

from conftest import make_expense, USER_A, USER_B


# ── Basic portion calculations ─────────────────────────────────────


def test_my_expense_empty_db(auth_client_a):
    data = auth_client_a.get("/api/my-expense-summary").json()
    assert data["my_total"] == 0.0
    assert data["total_shared_spend"] == 0.0


def test_my_expense_50_50_user_a(auth_client_a):
    """50/50 split: each user's portion is half."""
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=100, paid_by=USER_A, split_method="50/50",
    ))
    data = auth_client_a.get("/api/my-expense-summary").json()
    assert data["my_total"] == 50.0
    assert data["total_shared_spend"] == 100.0


def test_my_expense_50_50_user_b(auth_client_b):
    """50/50 split viewed from User B: their portion is also half."""
    auth_client_b.post("/api/expenses", json=make_expense(
        amount=100, paid_by=USER_A, split_method="50/50",
    ))
    data = auth_client_b.get("/api/my-expense-summary").json()
    assert data["my_total"] == 50.0


def test_my_expense_100_percent_a_paid_by_b(auth_client_a, auth_client_b):
    """100% Alice paid by Bob: Alice's portion = 100, Bob's = 0."""
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=100, paid_by=USER_B, split_method=f"100% {USER_A}",
    ))
    data_a = auth_client_a.get("/api/my-expense-summary").json()
    data_b = auth_client_b.get("/api/my-expense-summary").json()
    assert data_a["my_total"] == 100.0
    assert data_b["my_total"] == 0.0


def test_my_expense_100_percent_b_paid_by_a(auth_client_a, auth_client_b):
    """100% Bob paid by Alice: Alice's portion = 0, Bob's = 100."""
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=100, paid_by=USER_A, split_method=f"100% {USER_B}",
    ))
    data_a = auth_client_a.get("/api/my-expense-summary").json()
    data_b = auth_client_b.get("/api/my-expense-summary").json()
    assert data_a["my_total"] == 0.0
    assert data_b["my_total"] == 100.0


def test_my_expense_personal(auth_client_a):
    """Personal expense: only counts for the person who paid."""
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=75, paid_by=USER_A, split_method="Personal",
    ))
    data = auth_client_a.get("/api/my-expense-summary").json()
    assert data["my_total"] == 75.0
    assert data["total_shared_spend"] == 0.0


# ── Mixed expenses ─────────────────────────────────────────────────


def test_my_expense_mixed(auth_client_a):
    """Mixed split methods sum correctly."""
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=100, split_method="50/50", paid_by=USER_A,
    ))
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=60, split_method="Personal", paid_by=USER_A,
    ))
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=80, split_method=f"100% {USER_B}", paid_by=USER_A,
    ))
    data = auth_client_a.get("/api/my-expense-summary").json()
    # 50 (half of 100) + 60 (personal) + 0 (100% Bob) = 110
    assert data["my_total"] == 110.0
    # Shared = 100 (50/50) + 80 (100% Bob) = 180
    assert data["total_shared_spend"] == 180.0


# ── Exclusions ─────────────────────────────────────────────────────


def test_my_expense_excludes_payment(auth_client_a):
    """Payment category is excluded from my_total."""
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=100, split_method="50/50",
    ))
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=50, category="Payment", split_method=f"100% {USER_B}",
    ))
    data = auth_client_a.get("/api/my-expense-summary").json()
    assert data["my_total"] == 50.0


def test_my_expense_includes_reimbursement(auth_client_a):
    """Reimbursement (negative) reduces my_total."""
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=100, split_method="50/50",
    ))
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=-20, category="Reimbursement", split_method="50/50",
    ))
    data = auth_client_a.get("/api/my-expense-summary").json()
    # 50 (half of 100) + (-10) (half of -20) = 40
    assert data["my_total"] == 40.0


# ── Date filtering ─────────────────────────────────────────────────


def test_my_expense_only_current_month(auth_client_a):
    """Only current month expenses are included."""
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=100, split_method="50/50",
    ))
    last_month = date.today().replace(day=1) - timedelta(days=1)
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=200, split_method="50/50", date=str(last_month),
    ))
    data = auth_client_a.get("/api/my-expense-summary").json()
    assert data["my_total"] == 50.0


# ── Personal mode ─────────────────────────────────────────────────


def test_my_expense_personal_mode(auth_client_a):
    """In personal mode, my_total equals total personal spend."""
    auth_client_a.put("/api/settings", json={"app_mode": "personal"})
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=150, split_method="Personal", paid_by=USER_A,
    ))
    data = auth_client_a.get("/api/my-expense-summary").json()
    assert data["my_total"] == 150.0
    assert data["total_shared_spend"] == 0.0


# ── Blended mode ──────────────────────────────────────────────────


def test_my_expense_blended_personal_plus_shared(auth_client_a):
    """Blended: personal + shared portion combined correctly."""
    auth_client_a.put("/api/settings", json={"app_mode": "blended"})
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=40, split_method="Personal", paid_by=USER_A,
    ))
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=100, split_method="50/50", paid_by=USER_B,
    ))
    data = auth_client_a.get("/api/my-expense-summary").json()
    # 40 (personal) + 50 (half of 100) = 90
    assert data["my_total"] == 90.0
    assert data["total_shared_spend"] == 100.0
