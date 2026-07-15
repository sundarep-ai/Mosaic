"""
Cross-endpoint reconciliation tests (bucket 04 item #2).

Before this fix, a month containing a Reimbursement produced a different
"total" from each endpoint: the Analytics headline total included it, the
category/payer breakdowns excluded it, monthly-summary excluded it, and
my-expense-summary included it. These tests pin down the single convention
now documented in CLAUDE.md ("Money & currency"): Reimbursement nets into
every totals figure, and is excluded only from the `distribution` (percentage
-of-whole) view.
"""

from conftest import make_expense, USER_A, USER_B


def test_reimbursement_reconciles_across_analytics_and_summaries(auth_client_a):
    # Shared Groceries: Alice pays $100, 50/50.
    auth_client_a.post("/api/expenses", json=make_expense(
        category="Groceries", amount=100, paid_by=USER_A, split_method="50/50",
    ))
    # Shared Reimbursement: a $30 refund on a shared expense, 50/50, logged by Alice.
    auth_client_a.post("/api/expenses", json=make_expense(
        category="Reimbursement", amount=-30, paid_by=USER_A, split_method="50/50",
    ))
    # Alice's own personal expense, unaffected by splitting.
    auth_client_a.post("/api/expenses", json=make_expense(
        category="Dining", amount=40, paid_by=USER_A, split_method="Personal",
    ))

    analytics = auth_client_a.get("/api/analytics").json()
    monthly_summary = auth_client_a.get("/api/monthly-summary").json()
    my_expense = auth_client_a.get("/api/my-expense-summary").json()

    # total_spend nets the refund in: 100 - 30 + 40 = 110
    assert analytics["total_spend"] == 110.0

    # by_category is a totals view too — Reimbursement appears as its own
    # (negative) line, and the category bars sum to total_spend exactly.
    by_cat_sum = sum(c["amount"] for c in analytics["by_category"])
    assert by_cat_sum == analytics["total_spend"]

    # distribution excludes Reimbursement — only Groceries and Dining slice the pie.
    dist_cats = {d["category"] for d in analytics["distribution"]}
    assert dist_cats == {"Groceries", "Dining"}

    # Alice's net share: 50 (half of 100) + (-15) (half of -30) + 40 (personal) = 75
    assert analytics["my_share"] == 75.0

    # The category breakdown Alice sees on her dashboard must sum to the same
    # figure as her "Your Expense This Month" tile.
    monthly_sum = sum(item["amount"] for item in monthly_summary)
    assert monthly_sum == my_expense["my_total"]
    assert my_expense["my_total"] == analytics["my_share"]


# ── Odd-cent regression (bucket 08, item 3 — highest protection) ────────────


def test_odd_cent_split_reconciles_across_balance_share_summary_and_insights(auth_client_a):
    """A single $100.01 50/50 expense, viewed through four independent code
    paths (balance's SQL case expression, monthly-summary/my-expense-summary's
    shared _my_portion_expr, and Insights' separate Python _my_portion), must
    land on the exact same rounded-to-the-cent figure everywhere. Every prior
    test in this suite used round-dollar amounts, so a rounding/precision
    divergence between the SQL and Python portion implementations had no way
    to be caught."""
    auth_client_a.post("/api/expenses", json=make_expense(
        category="Groceries", amount=100.01, paid_by=USER_B, split_method="50/50",
    ))

    balance = auth_client_a.get("/api/balance").json()
    monthly_summary = auth_client_a.get("/api/monthly-summary").json()
    my_expense = auth_client_a.get("/api/my-expense-summary").json()
    insights = auth_client_a.get("/api/insights").json()

    # Alice's portion of a 50/50 split is the same figure regardless of who
    # paid — balance (SQL) reads it as "Alice owes Bob $X"; the category
    # breakdown and my-expense-summary (also SQL, via _my_portion_expr) read
    # it as her monthly spend; Insights (Python, via _my_portion) reads it in
    # the weekend/weekday breakdown. All four must agree to the cent.
    my_portion = my_expense["my_total"]
    assert my_portion > 0
    assert balance["amount"] == my_portion
    assert sum(item["amount"] for item in monthly_summary) == my_portion

    ww = insights["weekend_vs_weekday"]["your_expense"]
    insights_total = ww["weekday"]["total"] + ww["weekend"]["total"]
    assert insights_total == my_portion
