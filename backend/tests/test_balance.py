"""Tests for balance calculation and monthly summary."""

from conftest import make_expense, USER_A, USER_B


# ── Balance ─────────────────────────────────────────────────────────


def test_balance_empty_db(auth_client_a):
    data = auth_client_a.get("/api/balance").json()
    assert data["amount"] == 0
    assert data["description"] == "All settled up!"


def test_balance_50_50_a_pays(auth_client_a):
    """A pays $100 50/50 -> B owes A $50 -> balance = -50."""
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=100, paid_by=USER_A, split_method="50/50",
    ))
    data = auth_client_a.get("/api/balance").json()
    assert data["amount"] == -50.0
    assert USER_B in data["description"]
    assert "owes" in data["description"]


def test_balance_50_50_b_pays(auth_client_a):
    """B pays $100 50/50 -> A owes B $50 -> balance = +50."""
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=100, paid_by=USER_B, split_method="50/50",
    ))
    data = auth_client_a.get("/api/balance").json()
    assert data["amount"] == 50.0
    assert USER_A in data["description"]
    assert "owes" in data["description"]


def test_balance_100_percent_a_paid_by_b(auth_client_a):
    """B pays $100 for A's expense -> A owes B $100 -> balance = +100."""
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=100, paid_by=USER_B, split_method=f"100% {USER_A}",
    ))
    data = auth_client_a.get("/api/balance").json()
    assert data["amount"] == 100.0


def test_balance_100_percent_a_paid_by_a(auth_client_a):
    """A pays for own expense (100% Alice) -> no balance impact."""
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=100, paid_by=USER_A, split_method=f"100% {USER_A}",
    ))
    data = auth_client_a.get("/api/balance").json()
    assert data["amount"] == 0


def test_balance_100_percent_b_paid_by_a(auth_client_a):
    """A pays $100 for B's expense -> B owes A $100 -> balance = -100."""
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=100, paid_by=USER_A, split_method=f"100% {USER_B}",
    ))
    data = auth_client_a.get("/api/balance").json()
    assert data["amount"] == -100.0


def test_balance_personal_no_impact(auth_client_a):
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=500, paid_by=USER_A, split_method="Personal",
    ))
    data = auth_client_a.get("/api/balance").json()
    assert data["amount"] == 0
    assert data["description"] == "All settled up!"


def test_balance_multiple_expenses_net(auth_client_a):
    """A pays $200 50/50 (-100), B pays $100 50/50 (+50) -> net -50."""
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=200, paid_by=USER_A, split_method="50/50",
    ))
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=100, paid_by=USER_B, split_method="50/50",
    ))
    data = auth_client_a.get("/api/balance").json()
    assert data["amount"] == -50.0


def test_balance_settlement_zeroes_out(auth_client_a):
    """Payment settles the balance to zero."""
    # B pays $100 50/50 -> A owes B $50
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=100, paid_by=USER_B, split_method="50/50",
    ))
    # A settles by paying $50 for B's share (100% Bob)
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=50, paid_by=USER_A, split_method=f"100% {USER_B}",
        category="Payment",
    ))
    data = auth_client_a.get("/api/balance").json()
    assert data["amount"] == 0
    assert data["description"] == "All settled up!"


# ── Monthly Summary ─────────────────────────────────────────────────


def test_monthly_summary(auth_client_a):
    auth_client_a.post("/api/expenses", json=make_expense(category="Groceries", amount=80))
    auth_client_a.post("/api/expenses", json=make_expense(category="Dining", amount=45))
    auth_client_a.post("/api/expenses", json=make_expense(category="Groceries", amount=120))

    data = auth_client_a.get("/api/monthly-summary").json()
    cats = {item["category"]: item["amount"] for item in data}
    assert cats["Groceries"] == 200.0
    assert cats["Dining"] == 45.0


def test_monthly_summary_excludes_payment(auth_client_a):
    auth_client_a.post("/api/expenses", json=make_expense(category="Payment", amount=100))
    auth_client_a.post("/api/expenses", json=make_expense(category="Groceries", amount=50))

    data = auth_client_a.get("/api/monthly-summary").json()
    categories = [item["category"] for item in data]
    assert "Payment" not in categories
    assert "Groceries" in categories
