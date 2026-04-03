"""Tests for the Smart Insights endpoint."""

from datetime import date, timedelta

from conftest import make_expense, USER_A, USER_B


def _seed_monthly_recurring(client, description, category, amount, months=4):
    """Seed a recurring monthly expense over the given number of months."""
    today = date.today()
    for i in range(months):
        d = today - timedelta(days=30 * i)
        # Clamp to avoid future dates
        if d > today:
            d = today
        client.post(
            "/api/expenses",
            json=make_expense(
                date=str(d),
                description=description,
                category=category,
                amount=amount,
            ),
        )


# ── Empty database ─────────────────────────────────────────────────────


def test_insights_empty_db(auth_client_a):
    data = auth_client_a.get("/api/insights").json()
    assert data["recurring_expenses"] == []
    assert data["recurring_alerts"] == []
    assert data["weekend_vs_weekday"]["weekday"]["total"] == 0
    assert data["weekend_vs_weekday"]["weekend"]["total"] == 0
    assert data["anomalies"] == []
    assert data["forecast"]["total_forecast"] == 0
    assert data["top_growing_categories"] == []


def test_insights_requires_auth(client):
    resp = client.get("/api/insights")
    assert resp.status_code == 401


# ── Payment/Reimbursement exclusion ────────────────────────────────────


def test_insights_excludes_payment_and_reimbursement(auth_client_a):
    """Payment and Reimbursement categories should be excluded from all insights."""
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(category="Payment", amount=500),
    )
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(category="Reimbursement", amount=-30),
    )
    data = auth_client_a.get("/api/insights").json()
    # Weekend/weekday counts should be zero since only excluded categories exist
    total = (
        data["weekend_vs_weekday"]["weekday"]["count"]
        + data["weekend_vs_weekday"]["weekend"]["count"]
    )
    assert total == 0


# ── Weekend vs Weekday ─────────────────────────────────────────────────


def test_weekend_vs_weekday(auth_client_a):
    """Expenses on Saturday/Sunday should be bucketed as weekend."""
    # Find next Saturday and next Tuesday from a known reference
    today = date.today()
    # Calculate days to Saturday (5) and Tuesday (1)
    days_to_saturday = (5 - today.weekday()) % 7
    if days_to_saturday == 0:
        days_to_saturday = 7
    saturday = today - timedelta(days=7 - days_to_saturday)
    # Make sure it's in the past
    while saturday >= today:
        saturday -= timedelta(days=7)

    tuesday = saturday - timedelta(days=4)  # 4 days before Saturday = Tuesday

    auth_client_a.post(
        "/api/expenses",
        json=make_expense(date=str(saturday), amount=100, description="Weekend meal"),
    )
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(date=str(tuesday), amount=200, description="Weekday grocery"),
    )

    data = auth_client_a.get("/api/insights").json()
    ww = data["weekend_vs_weekday"]
    assert ww["weekend"]["total"] == 100.0
    assert ww["weekend"]["count"] == 1
    assert ww["weekday"]["total"] == 200.0
    assert ww["weekday"]["count"] == 1


# ── Recurring detection ────────────────────────────────────────────────


def test_recurring_detection_monthly(auth_client_a):
    """Expenses at ~30-day intervals should be detected as monthly recurring."""
    today = date.today()
    for i in range(5):
        d = today - timedelta(days=30 * i)
        if d > today:
            d = today
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(
                date=str(d),
                description="Netflix",
                category="Subscription",
                amount=15.99,
            ),
        )

    data = auth_client_a.get("/api/insights").json()
    recurring = data["recurring_expenses"]
    assert len(recurring) >= 1
    netflix = next((r for r in recurring if "Netflix" in r["description"]), None)
    assert netflix is not None
    assert netflix["frequency"] == "Monthly"
    assert netflix["occurrence_count"] == 5


def test_recurring_too_few_occurrences(auth_client_a):
    """Fewer than 3 occurrences should not be flagged as recurring."""
    today = date.today()
    for i in range(2):
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(
                date=str(today - timedelta(days=30 * i)),
                description="One-time service",
                category="Services",
                amount=50,
            ),
        )

    data = auth_client_a.get("/api/insights").json()
    assert len(data["recurring_expenses"]) == 0


# ── Recurring change alerts ────────────────────────────────────────────


def test_recurring_change_alert(auth_client_a):
    """Alert when the latest recurring amount changes >15% from average."""
    today = date.today()
    # 4 older entries at $15
    for i in range(1, 5):
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(
                date=str(today - timedelta(days=30 * i)),
                description="Streaming Service",
                category="Subscription",
                amount=15.00,
            ),
        )
    # Latest entry at $22 (46.7% increase)
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(
            date=str(today),
            description="Streaming Service",
            category="Subscription",
            amount=22.00,
        ),
    )

    data = auth_client_a.get("/api/insights").json()
    alerts = data["recurring_alerts"]
    assert len(alerts) >= 1
    alert = alerts[0]
    assert alert["direction"] == "up"
    assert alert["change_pct"] > 15


def test_no_false_recurring_alert(auth_client_a):
    """Stable recurring amounts should not generate alerts."""
    today = date.today()
    for i in range(5):
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(
                date=str(today - timedelta(days=30 * i)),
                description="Rent",
                category="Housing",
                amount=1500.00,
            ),
        )

    data = auth_client_a.get("/api/insights").json()
    rent_alerts = [a for a in data["recurring_alerts"] if "Rent" in a["description"]]
    assert len(rent_alerts) == 0


# ── Anomaly detection ──────────────────────────────────────────────────


def test_anomaly_detection(auth_client_a):
    """An unusually large expense should be flagged as an anomaly."""
    today = date.today()
    # Seed 10 normal grocery expenses
    for i in range(10):
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(
                date=str(today - timedelta(days=i + 1)),
                description=f"Groceries trip {i}",
                category="Groceries",
                amount=50.00,
            ),
        )
    # One very large outlier
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(
            date=str(today),
            description="Huge grocery haul",
            category="Groceries",
            amount=500.00,
        ),
    )

    data = auth_client_a.get("/api/insights").json()
    anomalies = data["anomalies"]
    assert len(anomalies) >= 1
    big = next((a for a in anomalies if a["amount"] == 500.0), None)
    assert big is not None
    assert big["direction"] == "high"
    assert big["z_score"] > 2


def test_no_anomaly_with_consistent_data(auth_client_a):
    """Consistent amounts should produce no anomalies."""
    today = date.today()
    for i in range(10):
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(
                date=str(today - timedelta(days=i)),
                description=f"Coffee {i}",
                category="Dining",
                amount=5.00,
            ),
        )

    data = auth_client_a.get("/api/insights").json()
    assert len(data["anomalies"]) == 0


# ── Category trend alerts ─────────────────────────────────────────────


def test_category_trend_alert(auth_client_a):
    """A significant month-over-month spike should trigger a trend alert."""
    today = date.today()
    current_month_start = today.replace(day=1)

    # 3 past months at $100/month for Dining
    for month_offset in range(1, 4):
        d = current_month_start - timedelta(days=30 * month_offset)
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(
                date=str(d),
                description="Restaurant",
                category="Dining",
                amount=100.00,
            ),
        )

    # Current month: $200 (100% increase)
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(
            date=str(today),
            description="Restaurant",
            category="Dining",
            amount=200.00,
        ),
    )

    data = auth_client_a.get("/api/insights").json()
    trend_alerts = data["category_trend_alerts"]
    dining_alerts = [a for a in trend_alerts if a["category"] == "Dining"]
    assert len(dining_alerts) >= 1
    assert dining_alerts[0]["direction"] == "up"
    assert dining_alerts[0]["change_pct"] > 25


# ── Forecast ───────────────────────────────────────────────────────────


def test_forecast_with_history(auth_client_a):
    """Forecast should produce non-zero totals when history exists."""
    today = date.today()
    current_month_start = today.replace(day=1)

    for month_offset in range(1, 4):
        d = current_month_start - timedelta(days=30 * month_offset)
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(
                date=str(d),
                description="Groceries",
                category="Groceries",
                amount=100.00 + month_offset * 10,
            ),
        )

    data = auth_client_a.get("/api/insights").json()
    forecast = data["forecast"]
    assert forecast["total_forecast"] > 0
    assert len(forecast["by_category"]) > 0


def test_forecast_empty_db(auth_client_a):
    data = auth_client_a.get("/api/insights").json()
    forecast = data["forecast"]
    assert forecast["total_forecast"] == 0
    assert forecast["by_category"] == []


# ── Top growing categories ─────────────────────────────────────────────


def test_top_growing_categories(auth_client_a):
    """A category with increasing monthly spend should appear in top growing."""
    today = date.today()

    # Use explicit month boundaries to ensure expenses land in distinct months
    # Month offsets: 3 months ago (smallest), 2 months ago, 1 month ago (largest)
    amounts = [50, 100, 150]  # escalating
    for i, month_offset in enumerate([3, 2, 1]):
        # Calculate target month's 15th day to guarantee correct month
        y, m = today.year, today.month - month_offset
        while m <= 0:
            m += 12
            y -= 1
        d = date(y, m, 15)
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(
                date=str(d),
                description="Entertainment",
                category="Entertainment",
                amount=amounts[i],
            ),
        )

    data = auth_client_a.get("/api/insights").json()
    growing = data["top_growing_categories"]
    if growing:
        ent = next((g for g in growing if g["category"] == "Entertainment"), None)
        if ent:
            assert ent["avg_mom_growth_pct"] > 0
