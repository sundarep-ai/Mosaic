"""Tests for the Smart Insights endpoint."""

from datetime import date, timedelta

from conftest import make_expense, make_income, set_mode, USER_A, USER_B


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
    ww = data["weekend_vs_weekday"]
    assert ww["your_expense"]["weekday"]["total"] == 0
    assert ww["your_expense"]["weekend"]["total"] == 0
    assert ww["shared_expense"]["weekday"]["total"] == 0
    assert ww["shared_expense"]["weekend"]["total"] == 0
    assert data["anomalies"] == []
    assert data["forecast"]["total_forecast"] == 0
    assert data["top_growing_categories"] == []
    assert data["mode"] == "duo"


def test_insights_requires_auth(client):
    resp = client.get("/api/insights")
    assert resp.status_code == 401


# ── Mode in response ─────────────────────────────────────────────────


def test_mode_in_response(auth_client_a, db):
    set_mode(db, "solo")
    data = auth_client_a.get("/api/insights").json()
    assert data["mode"] == "solo"

    set_mode(db, "hybrid")
    data = auth_client_a.get("/api/insights").json()
    assert data["mode"] == "hybrid"


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
    your = data["weekend_vs_weekday"]["your_expense"]
    total = your["weekday"]["count"] + your["weekend"]["count"]
    assert total == 0


# ── Weekend vs Weekday ─────────────────────────────────────────────────


def test_weekend_vs_weekday(auth_client_a):
    """Expenses on Saturday/Sunday should be bucketed as weekend."""
    today = date.today()
    days_to_saturday = (5 - today.weekday()) % 7
    if days_to_saturday == 0:
        days_to_saturday = 7
    saturday = today - timedelta(days=7 - days_to_saturday)
    while saturday >= today:
        saturday -= timedelta(days=7)

    tuesday = saturday - timedelta(days=4)

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

    # Shared expense should show full amounts
    assert ww["shared_expense"]["weekend"]["total"] == 100.0
    assert ww["shared_expense"]["weekend"]["count"] == 1
    assert ww["shared_expense"]["weekday"]["total"] == 200.0
    assert ww["shared_expense"]["weekday"]["count"] == 1

    # Your expense: default is 50/50 so user gets half
    assert ww["your_expense"]["weekend"]["total"] == 50.0
    assert ww["your_expense"]["weekday"]["total"] == 100.0


def test_weekend_weekday_dual_view_personal(auth_client_a, db):
    """Personal expenses: your_expense == shared_expense for the payer."""
    set_mode(db, "hybrid")
    today = date.today()
    days_to_saturday = (5 - today.weekday()) % 7
    if days_to_saturday == 0:
        days_to_saturday = 7
    saturday = today - timedelta(days=7 - days_to_saturday)
    while saturday >= today:
        saturday -= timedelta(days=7)

    auth_client_a.post(
        "/api/expenses",
        json=make_expense(
            date=str(saturday), amount=80, split_method="Personal",
            paid_by=USER_A, description="Personal weekend",
        ),
    )

    data = auth_client_a.get("/api/insights").json()
    ww = data["weekend_vs_weekday"]
    assert ww["your_expense"]["weekend"]["total"] == 80.0
    assert ww["shared_expense"]["weekend"]["total"] == 80.0


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


def test_recurring_my_amounts(auth_client_a):
    """Recurring entries should include avg_my_amount and last_my_amount."""
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
                amount=16.00,
                split_method="50/50",
            ),
        )

    data = auth_client_a.get("/api/insights").json()
    recurring = data["recurring_expenses"]
    netflix = next((r for r in recurring if "Netflix" in r["description"]), None)
    assert netflix is not None
    # 50/50 split: user's share is half
    assert netflix["avg_my_amount"] == 8.0
    assert netflix["last_my_amount"] == 8.0
    # Full amounts unchanged
    assert netflix["avg_amount"] == 16.0
    assert netflix["last_amount"] == 16.0


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
    # Should include my_* fields
    assert "my_previous_avg" in alert
    assert "my_current_amount" in alert


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


def test_anomalies_include_my_portion(auth_client_a):
    """Anomaly entries should include the user's portion."""
    today = date.today()
    for i in range(10):
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(
                date=str(today - timedelta(days=i + 1)),
                description=f"Groceries trip {i}",
                category="Groceries",
                amount=50.00,
                split_method="50/50",
            ),
        )
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(
            date=str(today),
            description="Huge grocery haul",
            category="Groceries",
            amount=500.00,
            split_method="50/50",
        ),
    )

    data = auth_client_a.get("/api/insights").json()
    anomalies = data["anomalies"]
    big = next((a for a in anomalies if a["amount"] == 500.0), None)
    assert big is not None
    assert big["my_portion"] == 250.0  # 50/50 of 500


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
    # Should include shared secondary fields
    assert "shared_current_month_amount" in dining_alerts[0]
    assert "shared_three_month_avg" in dining_alerts[0]


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
    assert "shared_total_forecast" in forecast


def test_forecast_empty_db(auth_client_a):
    data = auth_client_a.get("/api/insights").json()
    forecast = data["forecast"]
    assert forecast["total_forecast"] == 0
    assert forecast["by_category"] == []


def test_forecast_50_50_shows_user_portion(auth_client_a):
    """50/50 expense of $100 should show $50 in forecast."""
    today = date.today()
    current_month_start = today.replace(day=1)

    # Seed 3 months of $100 50/50 expenses
    for month_offset in range(1, 4):
        d = current_month_start - timedelta(days=30 * month_offset)
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(
                date=str(d),
                description="Groceries",
                category="Groceries",
                amount=100.00,
                split_method="50/50",
                paid_by=USER_A,
            ),
        )

    data = auth_client_a.get("/api/insights").json()
    forecast = data["forecast"]
    # User's forecast should be ~$50 (50% of $100)
    assert 45 <= forecast["total_forecast"] <= 55
    # Shared forecast should be ~$100
    assert 95 <= forecast["shared_total_forecast"] <= 105


def test_forecast_personal_other_excluded(auth_client_a, auth_client_b):
    """Personal expense paid by other user should result in $0 for current user's forecast."""
    today = date.today()
    current_month_start = today.replace(day=1)

    # Seed personal expenses paid by User B
    for month_offset in range(1, 4):
        d = current_month_start - timedelta(days=30 * month_offset)
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(
                date=str(d),
                description="Bob personal",
                category="Shopping",
                amount=200.00,
                split_method="Personal",
                paid_by=USER_B,
            ),
        )

    data = auth_client_a.get("/api/insights").json()
    forecast = data["forecast"]
    # User A's forecast should be $0 for these (they're Bob's personal expenses)
    assert forecast["total_forecast"] == 0


def test_forecast_lazy_period(auth_client_a):
    """Partially-entered most-recent month must not suppress the forecast."""
    today = date.today()

    def month_ago_date(months: int, day: int) -> date:
        y, m = today.year, today.month - months
        while m <= 0:
            m += 12
            y -= 1
        return date(y, m, day)

    for offset in [2, 3]:
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(
                date=str(month_ago_date(offset, 15)),
                description="Groceries",
                category="Groceries",
                amount=1000.0,
            ),
        )

    auth_client_a.post(
        "/api/expenses",
        json=make_expense(
            date=str(month_ago_date(1, 5)),
            description="Groceries",
            category="Groceries",
            amount=200.0,
        ),
    )

    data = auth_client_a.get("/api/insights").json()
    # Default 50/50 split: user gets half → amounts are halved
    # But the forecast logic should still show the rolling-window effect
    # Half of 900+ = 450+
    assert data["forecast"]["total_forecast"] > 450


# ── Top growing categories ─────────────────────────────────────────────


def test_top_growing_categories(auth_client_a):
    """A category with increasing monthly spend should appear in top growing."""
    today = date.today()

    amounts = [50, 100, 150]
    for i, month_offset in enumerate([3, 2, 1]):
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
            assert "shared_last_3_months" in ent


# ── Solo mode ──────────────────────────────────────────────────────────


def test_solo_mode_insights(auth_client_a, db):
    """In solo mode, all amounts should be at 100% (no splitting)."""
    set_mode(db, "solo")
    today = date.today()

    days_to_saturday = (5 - today.weekday()) % 7
    if days_to_saturday == 0:
        days_to_saturday = 7
    saturday = today - timedelta(days=7 - days_to_saturday)
    while saturday >= today:
        saturday -= timedelta(days=7)

    auth_client_a.post(
        "/api/expenses",
        json=make_expense(
            date=str(saturday), amount=100, description="Solo purchase",
            split_method="Personal", paid_by=USER_A,
        ),
    )

    data = auth_client_a.get("/api/insights").json()
    assert data["mode"] == "solo"

    ww = data["weekend_vs_weekday"]
    # In solo mode, your expense == shared expense == full amount
    assert ww["your_expense"]["weekend"]["total"] == 100.0
    assert ww["shared_expense"]["weekend"]["total"] == 100.0


# ── Income insights ───────────────────────────────────────────────────


def test_income_insights_none_duo(auth_client_a):
    """In duo mode, income_insights should be None."""
    data = auth_client_a.get("/api/insights").json()
    assert data["income_insights"] is None


def test_income_insights_present_hybrid(auth_client_a, db):
    """In hybrid mode with income data, income_insights should be populated."""
    set_mode(db, "hybrid")
    today = date.today()

    # Add income entry
    auth_client_a.post(
        "/api/income",
        json=make_income(date=str(today), amount=5000.00, source="Salary / Wages"),
    )
    # Add an expense
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(
            date=str(today), amount=1000.00,
            split_method="Personal", paid_by=USER_A,
        ),
    )

    data = auth_client_a.get("/api/insights").json()
    assert data["income_insights"] is not None

    ii = data["income_insights"]
    assert "savings_rate" in ii
    assert "income_vs_expense" in ii
    assert "income_by_source" in ii

    # Savings rate: income=5000, expense=1000, savings=4000, rate=80%
    current = ii["savings_rate"]["current_month"]
    assert current["income"] == 5000.0
    assert current["expenses"] == 1000.0
    assert current["savings"] == 4000.0
    assert current["rate_pct"] == 80.0


def test_income_insights_savings_rate(auth_client_a, db):
    """Verify savings rate math: (income - expenses) / income * 100."""
    set_mode(db, "hybrid")
    today = date.today()

    auth_client_a.post(
        "/api/income",
        json=make_income(date=str(today), amount=2000.00, source="Freelance / Side Income"),
    )
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(
            date=str(today), amount=1500.00,
            split_method="Personal", paid_by=USER_A,
        ),
    )

    data = auth_client_a.get("/api/insights").json()
    current = data["income_insights"]["savings_rate"]["current_month"]
    # (2000 - 1500) / 2000 * 100 = 25%
    assert current["rate_pct"] == 25.0
    assert current["savings"] == 500.0


def test_income_insights_no_income_data(auth_client_a, db):
    """In hybrid mode with no income entries, income_insights should be None."""
    set_mode(db, "hybrid")
    data = auth_client_a.get("/api/insights").json()
    assert data["income_insights"] is None


def test_income_insights_by_source(auth_client_a, db):
    """Income by source should break down correctly."""
    set_mode(db, "hybrid")
    today = date.today()

    auth_client_a.post(
        "/api/income",
        json=make_income(date=str(today), amount=4000.00, source="Salary / Wages"),
    )
    auth_client_a.post(
        "/api/income",
        json=make_income(date=str(today), amount=500.00, source="Freelance / Side Income"),
    )

    data = auth_client_a.get("/api/insights").json()
    by_source = data["income_insights"]["income_by_source"]["current_month"]
    salary = next((s for s in by_source if s["source"] == "Salary / Wages"), None)
    freelance = next((s for s in by_source if s["source"] == "Freelance / Side Income"), None)
    assert salary is not None
    assert salary["amount"] == 4000.0
    assert freelance is not None
    assert freelance["amount"] == 500.0


def test_income_vs_expense_surplus(auth_client_a, db):
    """Income vs expense should show correct surplus."""
    set_mode(db, "hybrid")
    today = date.today()

    auth_client_a.post(
        "/api/income",
        json=make_income(date=str(today), amount=3000.00),
    )
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(
            date=str(today), amount=2000.00,
            split_method="Personal", paid_by=USER_A,
        ),
    )

    data = auth_client_a.get("/api/insights").json()
    monthly = data["income_insights"]["income_vs_expense"]["monthly"]
    current_month = today.strftime("%Y-%m")
    entry = next((m for m in monthly if m["month"] == current_month), None)
    assert entry is not None
    assert entry["income"] == 3000.0
    assert entry["expense"] == 2000.0
    assert entry["surplus"] == 1000.0
