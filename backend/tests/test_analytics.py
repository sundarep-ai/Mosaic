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
    """Assert row identity and order, not just length/sortedness — the five
    *smallest* amounts sorted descending would satisfy the old assertions
    just as well as the real top 5, silently hiding a wrong-end sort bug."""
    amounts = [10, 50, 30, 80, 20, 60]
    for amt in amounts:
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(description=f"Item {amt}", amount=amt),
        )
    data = auth_client_a.get("/api/analytics").json()
    assert len(data["top_expenses"]) == 5
    top = [(e["description"], e["amount"]) for e in data["top_expenses"]]
    # The 10 must be dropped (6 expenses, only top 5 kept), rest descending.
    assert top == [
        ("Item 80", 80.0),
        ("Item 60", 60.0),
        ("Item 50", 50.0),
        ("Item 30", 30.0),
        ("Item 20", 20.0),
    ]


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


def test_analytics_reimbursement_in_total_spend(auth_client_a):
    """Reimbursements should reduce total_spend (money returned)."""
    auth_client_a.post("/api/expenses", json=make_expense(category="Groceries", amount=200))
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(category="Reimbursement", amount=-50),
    )
    data = auth_client_a.get("/api/analytics").json()
    assert data["total_spend"] == 150.0


def test_analytics_reimbursement_excluded_from_distribution(auth_client_a):
    """Distribution (percentage-of-whole) excludes Reimbursement — a refund
    can't sensibly own a slice of a pie chart."""
    auth_client_a.post("/api/expenses", json=make_expense(category="Groceries", amount=100))
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(category="Reimbursement", amount=-30),
    )
    data = auth_client_a.get("/api/analytics").json()
    dist_cats = [d["category"] for d in data["distribution"]]
    assert "Reimbursement" not in dist_cats


def test_analytics_reimbursement_included_in_by_category(auth_client_a):
    """by_category is a totals view, so Reimbursement nets in as its own
    (typically negative) line — this is what keeps it reconciled with
    total_spend (see the Reimbursement convention note in CLAUDE.md)."""
    auth_client_a.post("/api/expenses", json=make_expense(category="Groceries", amount=100))
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(category="Reimbursement", amount=-30),
    )
    data = auth_client_a.get("/api/analytics").json()
    by_cats = {c["category"]: c["amount"] for c in data["by_category"]}
    assert by_cats["Reimbursement"] == -30.0
    assert sum(by_cats.values()) == data["total_spend"]


def test_analytics_reimbursement_nets_into_payer_breakdown(auth_client_a):
    """by_payer is a totals view, so a payer's Reimbursement nets into their total."""
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(paid_by=USER_A, category="Groceries", amount=100),
    )
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(paid_by=USER_A, category="Reimbursement", amount=-30),
    )
    data = auth_client_a.get("/api/analytics").json()
    payers = {p["payer"]: p for p in data["by_payer"]}
    assert payers[USER_A]["amount"] == 70.0
    assert payers[USER_A]["count"] == 2


def test_analytics_reimbursement_excluded_from_top_expenses(auth_client_a):
    """Reimbursement should not appear in top 5 largest outlays."""
    auth_client_a.post("/api/expenses", json=make_expense(category="Groceries", amount=50))
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(category="Reimbursement", amount=-200),
    )
    data = auth_client_a.get("/api/analytics").json()
    top_cats = [e["category"] for e in data["top_expenses"]]
    assert "Reimbursement" not in top_cats


def test_analytics_reimbursement_kept_in_over_time(auth_client_a):
    """Reimbursement should still appear in spending velocity (over_time)."""
    auth_client_a.post("/api/expenses", json=make_expense(category="Groceries", amount=100))
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(category="Reimbursement", amount=-30),
    )
    data = auth_client_a.get("/api/analytics").json()
    # over_time includes all non-Payment expenses, so total should reflect the reimbursement
    total_over_time = sum(m["amount"] for m in data["over_time"])
    assert total_over_time == 70.0


def test_analytics_reimbursement_kept_in_split_method(auth_client_a):
    """Reimbursement should still appear in by_split_method."""
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(category="Groceries", amount=100, split_method="50/50"),
    )
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(category="Reimbursement", amount=-30, split_method="50/50"),
    )
    data = auth_client_a.get("/api/analytics").json()
    splits = {s["method"]: s["amount"] for s in data["by_split_method"]}
    assert splits["50/50"] == 70.0


def test_analytics_distribution_percentages_exclude_reimbursement(auth_client_a):
    """Distribution percentages should be calculated without Reimbursement."""
    auth_client_a.post("/api/expenses", json=make_expense(category="Groceries", amount=75))
    auth_client_a.post("/api/expenses", json=make_expense(category="Dining", amount=25))
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(category="Reimbursement", amount=-10),
    )
    data = auth_client_a.get("/api/analytics").json()
    dist = {d["category"]: d["percentage"] for d in data["distribution"]}
    assert "Reimbursement" not in dist
    # Percentages should still sum to 100 based on Groceries + Dining only
    assert dist["Groceries"] == 75.0
    assert dist["Dining"] == 25.0


# ── my_share ───────────────────────────────────────────────────────


def test_analytics_my_share_empty(auth_client_a):
    """my_share is 0 when no expenses."""
    data = auth_client_a.get("/api/analytics").json()
    assert data["my_share"] == 0


def test_analytics_my_share_50_50(auth_client_a):
    """50/50 expense: my_share is half for User A."""
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=200, split_method="50/50", paid_by=USER_A,
    ))
    data = auth_client_a.get("/api/analytics").json()
    assert data["my_share"] == 100.0


def test_analytics_my_share_100_percent(auth_client_a, auth_client_b):
    """100% Alice: A's share is full, B's share is 0."""
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=80, split_method=f"100% {USER_A}", paid_by=USER_B,
    ))
    data_a = auth_client_a.get("/api/analytics").json()
    data_b = auth_client_b.get("/api/analytics").json()
    assert data_a["my_share"] == 80.0
    assert data_b["my_share"] == 0.0


def test_analytics_my_share_excludes_payment(auth_client_a):
    """Payment is excluded from my_share."""
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=100, split_method="50/50",
    ))
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=50, category="Payment", split_method=f"100% {USER_B}",
    ))
    data = auth_client_a.get("/api/analytics").json()
    assert data["my_share"] == 50.0


def test_analytics_my_share_includes_reimbursement(auth_client_a):
    """Reimbursement reduces my_share."""
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=100, split_method="50/50",
    ))
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=-30, category="Reimbursement", split_method="50/50",
    ))
    data = auth_client_a.get("/api/analytics").json()
    # 50 (half of 100) + (-15) (half of -30) = 35
    assert data["my_share"] == 35.0


def test_analytics_my_share_personal(auth_client_a):
    """In personal mode, my_share equals total_spend."""
    auth_client_a.put("/api/settings", json={"app_mode": "personal"})
    auth_client_a.post("/api/expenses", json=make_expense(
        amount=120, split_method="Personal", paid_by=USER_A,
    ))
    data = auth_client_a.get("/api/analytics").json()
    assert data["my_share"] == data["total_spend"]
    assert data["my_share"] == 120.0
