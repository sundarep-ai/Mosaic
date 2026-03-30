"""Tests for analytics aggregation endpoint."""

from datetime import date, timedelta

from conftest import make_expense, USER_A, USER_B


def test_analytics_empty_db(auth_client_a):
    data = auth_client_a.get("/api/analytics").json()
    assert data["total_spend"] == 0
    assert data["total_shared_spend"] == 0
    assert data["by_category"] == []
    assert data["top_expenses"] == []


def test_analytics_total_spend(auth_client_a):
    auth_client_a.post("/api/expenses", json=make_expense(amount=100))
    auth_client_a.post("/api/expenses", json=make_expense(amount=200))
    data = auth_client_a.get("/api/analytics").json()
    assert data["total_spend"] == 300.0


def test_analytics_shared_vs_personal(auth_client_a):
    auth_client_a.post("/api/expenses", json=make_expense(amount=100, split_method="50/50"))
    auth_client_a.post("/api/expenses", json=make_expense(amount=50, split_method="Personal"))
    data = auth_client_a.get("/api/analytics").json()
    assert data["total_spend"] == 150.0
    assert data["total_shared_spend"] == 100.0


def test_analytics_by_category(auth_client_a):
    auth_client_a.post("/api/expenses", json=make_expense(category="Groceries", amount=100))
    auth_client_a.post("/api/expenses", json=make_expense(category="Dining", amount=50))
    data = auth_client_a.get("/api/analytics").json()
    cats = {c["category"]: c["amount"] for c in data["by_category"]}
    assert cats["Groceries"] == 100.0
    assert cats["Dining"] == 50.0


def test_analytics_distribution_percentages(auth_client_a):
    auth_client_a.post("/api/expenses", json=make_expense(category="Groceries", amount=75))
    auth_client_a.post("/api/expenses", json=make_expense(category="Dining", amount=25))
    data = auth_client_a.get("/api/analytics").json()
    dist = {d["category"]: d["percentage"] for d in data["distribution"]}
    assert dist["Groceries"] == 75.0
    assert dist["Dining"] == 25.0


def test_analytics_by_payer(auth_client_a):
    auth_client_a.post("/api/expenses", json=make_expense(paid_by=USER_A, amount=100))
    auth_client_a.post("/api/expenses", json=make_expense(paid_by=USER_B, amount=200))
    data = auth_client_a.get("/api/analytics").json()
    payers = {p["payer"]: p["amount"] for p in data["by_payer"]}
    assert payers[USER_A] == 100.0
    assert payers[USER_B] == 200.0


def test_analytics_by_split_method(auth_client_a):
    auth_client_a.post("/api/expenses", json=make_expense(split_method="50/50", amount=80))
    auth_client_a.post("/api/expenses", json=make_expense(split_method="Personal", amount=40))
    data = auth_client_a.get("/api/analytics").json()
    splits = {s["method"]: s["amount"] for s in data["by_split_method"]}
    assert splits["50/50"] == 80.0
    assert splits["Personal"] == 40.0


def test_analytics_top_expenses(auth_client_a):
    for amt in [10, 50, 30, 80, 20, 60]:
        auth_client_a.post("/api/expenses", json=make_expense(amount=amt))
    data = auth_client_a.get("/api/analytics").json()
    assert len(data["top_expenses"]) == 5
    amounts = [e["amount"] for e in data["top_expenses"]]
    assert amounts == sorted(amounts, reverse=True)


def test_analytics_excludes_payment(auth_client_a):
    auth_client_a.post("/api/expenses", json=make_expense(category="Payment", amount=100))
    auth_client_a.post("/api/expenses", json=make_expense(category="Groceries", amount=50))
    data = auth_client_a.get("/api/analytics").json()
    assert data["total_spend"] == 50.0
    cats = [c["category"] for c in data["by_category"]]
    assert "Payment" not in cats


def test_analytics_date_filter(auth_client_a):
    today = date.today()
    old_date = today - timedelta(days=60)
    auth_client_a.post("/api/expenses", json=make_expense(date=str(today), amount=100))
    auth_client_a.post("/api/expenses", json=make_expense(date=str(old_date), amount=200))

    data = auth_client_a.get(
        f"/api/analytics?start_date={today}&end_date={today}"
    ).json()
    assert data["total_spend"] == 100.0
