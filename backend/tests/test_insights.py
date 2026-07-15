"""Tests for the Smart Insights endpoint."""

from datetime import date, timedelta
from decimal import Decimal

from conftest import make_expense, make_income, set_mode, USER_A, USER_B
from models import Expense


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
    assert data["mode"] == "shared"


def test_insights_requires_auth(client):
    resp = client.get("/api/insights")
    assert resp.status_code == 401


# ── Mode in response ─────────────────────────────────────────────────


def test_mode_in_response(auth_client_a, db):
    set_mode(db, "personal")
    data = auth_client_a.get("/api/insights").json()
    assert data["mode"] == "personal"

    set_mode(db, "blended")
    data = auth_client_a.get("/api/insights").json()
    assert data["mode"] == "blended"


# ── Payload caching ─────────────────────────────────────────────────────


def test_insights_cache_hit_avoids_recomputation(auth_client_a, monkeypatch):
    """A second identical /insights call must be served from cache, not
    recompute recurring detection from scratch -- the entire point of
    this bucket's item 1."""
    import routes.insights as insights_mod
    calls = {"n": 0}
    original = insights_mod._detect_recurring

    def counting(*args, **kwargs):
        calls["n"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(insights_mod, "_detect_recurring", counting)

    auth_client_a.get("/api/insights")
    auth_client_a.get("/api/insights")
    assert calls["n"] == 1


def test_insights_cache_invalidated_by_expense_mutation(auth_client_a):
    """Creating an expense must invalidate any previously-cached payload --
    otherwise a cached page would go stale until the next calendar day."""
    data1 = auth_client_a.get("/api/insights").json()
    assert data1["forecast"]["on_pace"]["mtd_actual"] == 0

    today = date.today()
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(
            date=str(today.replace(day=1)), description="New spend", category="Groceries",
            amount=42.00, split_method="Personal", paid_by=USER_A,
        ),
    )

    data2 = auth_client_a.get("/api/insights").json()
    assert data2["forecast"]["on_pace"]["mtd_actual"] == 42.0


def test_insights_cache_is_per_user(auth_client_a, auth_client_b):
    """Alice's and Bob's cached payloads must not collide -- each reflects
    their own portion of the same expenses."""
    today = date.today()
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(
            date=str(today), description="Shared groceries", category="Groceries",
            amount=100.00, split_method="50/50",
        ),
    )
    data_a = auth_client_a.get("/api/insights").json()
    data_b = auth_client_b.get("/api/insights").json()
    assert data_a["forecast"]["on_pace"]["mtd_actual"] == 50.0
    assert data_b["forecast"]["on_pace"]["mtd_actual"] == 50.0
    assert data_a["forecast"]["on_pace"]["shared_mtd_actual"] == 100.0


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
    set_mode(db, "blended")
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


def test_recurring_detects_bimonthly(auth_client_a):
    """A ~61-day cadence used to fall in the old dead zone (36-79 days) and
    could never be detected. The period-grid matcher must classify it."""
    today = date.today()
    d3 = today
    d2 = d3 - timedelta(days=61)
    d1 = d2 - timedelta(days=60)
    d0 = d1 - timedelta(days=62)
    for d in (d0, d1, d2, d3):
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(date=str(d), description="Storage Unit", category="Home Care", amount=45.00),
        )

    data = auth_client_a.get("/api/insights").json()
    storage = next((r for r in data["recurring_expenses"] if r["description"] == "Storage Unit"), None)
    assert storage is not None
    assert storage["frequency"] == "Bimonthly"
    assert storage["occurrence_count"] == 4


def test_recurring_detects_semiannual(auth_client_a):
    """A ~183-day cadence used to fall in the old dead zone (101-339 days)
    and could never be detected -- a semi-annual insurance premium."""
    today = date.today()
    d2 = today
    d1 = d2 - timedelta(days=183)
    d0 = d1 - timedelta(days=182)
    for d in (d0, d1, d2):
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(date=str(d), description="Car Insurance Premium", category="Car Insurance", amount=520.00),
        )

    data = auth_client_a.get("/api/insights").json()
    premium = next((r for r in data["recurring_expenses"] if r["description"] == "Car Insurance Premium"), None)
    assert premium is not None
    assert premium["frequency"] == "Semiannual"


def test_recurring_same_day_duplicates_collapse_into_one_occurrence(auth_client_a):
    """Two same-day postings (e.g. a duplicate charge) must sum into a
    single occurrence, not inject a 0-day interval into the sequence."""
    today = date.today()
    day0 = today
    day1 = day0 - timedelta(days=30)
    day2 = day1 - timedelta(days=30)
    day3 = day2 - timedelta(days=30)
    for d in (day3, day2, day1):
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(date=str(d), description="Netflix", category="Subscription", amount=15.99),
        )
    # Two postings on the same (most recent) day -- e.g. billed twice.
    for _ in range(2):
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(date=str(day0), description="Netflix", category="Subscription", amount=15.99),
        )

    data = auth_client_a.get("/api/insights").json()
    netflix = next((r for r in data["recurring_expenses"] if r["description"] == "Netflix"), None)
    assert netflix is not None
    assert netflix["frequency"] == "Monthly"
    # 4 distinct days, not 5 raw postings.
    assert netflix["occurrence_count"] == 4
    assert netflix["last_amount"] == 31.98


def test_recurring_one_missed_month_still_classifies_monthly(auth_client_a):
    """A single skipped cycle (interval ~60 days instead of ~30) used to
    land the median interval in the old 36-79 day dead zone, so the whole
    series went undetected. It must still classify as Monthly."""
    today = date.today()
    day_a = today - timedelta(days=90)
    day_b = today - timedelta(days=60)  # 30 days after day_a: on time
    day_c = today  # 60 days after day_b: one month was missed
    for d in (day_a, day_b, day_c):
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(date=str(d), description="Gym Membership", category="Healthcare", amount=40.00),
        )

    data = auth_client_a.get("/api/insights").json()
    gym = next((r for r in data["recurring_expenses"] if r["description"] == "Gym Membership"), None)
    assert gym is not None
    assert gym["frequency"] == "Monthly"
    assert gym["occurrence_count"] == 3


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


# ── Price-step alerts, new-subscription alerts, and dismiss (bucket 10) ─


def test_price_step_alert_reports_exact_step_facts(auth_client_a):
    """Change-point detection: median of the last occurrence(s) vs the
    prior stable plateau, reported with the facts that matter -- previous
    price, new price, since when, annualized cost delta -- not a vague
    percentage derived from comparing the latest amount to an all-time mean
    that hasn't caught up yet."""
    today = date.today()
    for i in range(4, 0, -1):
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(
                date=str(today - timedelta(days=30 * i)),
                description="Netflix", category="Subscription", amount=15.99,
            ),
        )
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(date=str(today), description="Netflix", category="Subscription", amount=17.99),
    )

    data = auth_client_a.get("/api/insights").json()
    alerts = [a for a in data["recurring_alerts"] if a["description"] == "Netflix"]
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["alert_type"] == "price_step"
    assert alert["previous_avg"] == 15.99
    assert alert["current_amount"] == 17.99
    assert alert["direction"] == "up"
    assert alert["since"] == str(today)
    assert alert["confirmations"] == 1
    assert alert["confirmations_needed"] == 3
    assert alert["annualized_delta"] == round((17.99 - 15.99) * (365.25 / 30.44), 2)
    assert "series_key" in alert


def test_price_step_alert_goes_quiet_after_three_confirmations(auth_client_a):
    """Once 3 occurrences confirm the new price, it's the accepted baseline
    and the alert stops firing -- it must not linger forever, and it must
    not re-fire every visit while the same step is still being confirmed."""
    today = date.today()
    for i in range(6, 2, -1):
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(
                date=str(today - timedelta(days=30 * i)),
                description="Netflix", category="Subscription", amount=15.99,
            ),
        )
    for i in range(2, -1, -1):
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(
                date=str(today - timedelta(days=30 * i)),
                description="Netflix", category="Subscription", amount=17.99,
            ),
        )

    data = auth_client_a.get("/api/insights").json()
    assert not any(a["description"] == "Netflix" for a in data["recurring_alerts"])


def test_price_step_alert_dismiss_persists(auth_client_a):
    """A dismissed price-step alert must stay dismissed across separate
    /insights requests -- the entire point of the alert-state table."""
    today = date.today()
    for i in range(4, 0, -1):
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(
                date=str(today - timedelta(days=30 * i)),
                description="Netflix", category="Subscription", amount=15.99,
            ),
        )
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(date=str(today), description="Netflix", category="Subscription", amount=17.99),
    )

    data = auth_client_a.get("/api/insights").json()
    alert = next(a for a in data["recurring_alerts"] if a["description"] == "Netflix")

    resp = auth_client_a.post(
        "/api/insights/alerts/dismiss",
        json={"series_key": alert["series_key"], "alert_type": "price_step"},
    )
    assert resp.status_code == 200

    data2 = auth_client_a.get("/api/insights").json()
    assert not any(a["description"] == "Netflix" for a in data2["recurring_alerts"])

    # A third call proves this isn't just a same-request fluke -- the
    # dismissal is read back from the persistence table, not held in memory
    # only for the request that dismissed it.
    data3 = auth_client_a.get("/api/insights").json()
    assert not any(a["description"] == "Netflix" for a in data3["recurring_alerts"])


def test_dismiss_alert_rejects_invalid_alert_type(auth_client_a):
    resp = auth_client_a.post(
        "/api/insights/alerts/dismiss",
        json={"series_key": "Subscription::Netflix", "alert_type": "bogus"},
    )
    assert resp.status_code == 400


def test_new_subscription_detected(auth_client_a):
    """A series first seen <60 days ago with >=2 occurrences on a fixed
    cadence is flagged as a new subscription -- well before it would
    accumulate the 3 occurrences _detect_recurring itself requires."""
    today = date.today()
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(date=str(today - timedelta(days=14)), description="Disney Plus", category="Subscription", amount=9.99),
    )
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(date=str(today), description="Disney Plus", category="Subscription", amount=9.99),
    )

    data = auth_client_a.get("/api/insights").json()
    disney = next((a for a in data["new_subscription_alerts"] if a["description"] == "Disney Plus"), None)
    assert disney is not None
    assert disney["alert_type"] == "new_subscription"
    assert disney["occurrence_count"] == 2
    assert disney["first_seen"] == str(today - timedelta(days=14))


def test_new_subscription_not_detected_when_older_than_60_days(auth_client_a):
    """A series whose first occurrence is >=60 days old is no longer 'new',
    regardless of how many occurrences it has."""
    today = date.today()
    for days_ago in (70, 56, 0):
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(
                date=str(today - timedelta(days=days_ago)),
                description="Disney Plus", category="Subscription", amount=9.99,
            ),
        )

    data = auth_client_a.get("/api/insights").json()
    assert not any(a["description"] == "Disney Plus" for a in data["new_subscription_alerts"])


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


def test_anomaly_uses_median_and_mad_not_mean_and_stdev(auth_client_a):
    """Anomaly entries now report category_median/category_mad, not the old
    mean/stdev -- amounts are heavy-right-tailed, so mean/stdev are the
    wrong descriptive statistic for this data."""
    today = date.today()
    for i in range(10):
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(
                date=str(today - timedelta(days=i + 1)), description=f"Groceries trip {i}",
                category="Groceries", amount=50.00,
            ),
        )
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(date=str(today), description="Huge grocery haul", category="Groceries", amount=500.00),
    )

    data = auth_client_a.get("/api/insights").json()
    big = next(a for a in data["anomalies"] if a["amount"] == 500.0)
    assert "category_median" in big
    assert "category_mad" in big
    assert "category_mean" not in big
    assert "category_std" not in big


def test_anomaly_drops_low_direction_entirely(auth_client_a):
    """An unusually CHEAP purchase is not information worth surfacing --
    only high anomalies are ever flagged."""
    today = date.today()
    for i in range(10):
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(
                date=str(today - timedelta(days=i + 1)), description=f"Groceries trip {i}",
                category="Groceries", amount=50.00,
            ),
        )
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(date=str(today), description="Unusually cheap trip", category="Groceries", amount=2.00),
    )

    data = auth_client_a.get("/api/insights").json()
    cheap = [a for a in data["anomalies"] if a["amount"] == 2.0]
    assert cheap == []
    assert all(a["direction"] == "high" for a in data["anomalies"])


def test_anomaly_leave_one_out_excludes_candidate_from_its_own_baseline():
    """The candidate's own amount must not appear in the median/MAD it's
    compared against -- otherwise the "usual" figure reported alongside the
    anomaly is itself pulled toward the outlier. With baseline [10, 20, 30,
    40] (median 25) and a $1000 candidate, including the candidate in its
    own baseline (5 values) shifts the computed median to 30 -- a real,
    observable bias -- whereas excluding it (leave-one-out, 4 values)
    correctly reports the true baseline median of 25."""
    from routes.insights import _detect_anomalies

    today = date.today()
    expenses = []
    exp_id = 1
    for amt in ("10.00", "20.00", "30.00", "40.00"):
        expenses.append(Expense(
            id=exp_id, date=today - timedelta(days=exp_id + 2), description=f"Shopping trip {exp_id}",
            amount=Decimal(amt), category="Shopping", paid_by=USER_A, split_method="Personal",
        ))
        exp_id += 1
    expenses.append(Expense(
        id=exp_id, date=today, description="Huge shopping spree",
        amount=Decimal("1000.00"), category="Shopping", paid_by=USER_A, split_method="Personal",
    ))

    anomalies = _detect_anomalies(expenses, USER_A, USER_B)
    big = next(a for a in anomalies if a["amount"] == 1000.0)
    # Leave-one-out: median/MAD of [10, 20, 30, 40] only -- NOT the
    # naive/inclusive median of 30 that including the $1000 itself would give.
    assert big["category_median"] == 25.0
    assert big["category_mad"] == 10.0


# ── Category trend alerts (bucket 10, item 3: prorate + attribution) ───


def test_category_trend_alert(auth_client_a, monkeypatch):
    """A significant month-over-month spike should trigger a trend alert.

    Uses a distinct description per expense (and disables fuzzy clustering)
    so none of them coincidentally cluster into a single recurring series --
    this is a genuinely one-off dining splurge, not a subscription price
    step, and the two must not be conflated."""
    _no_fuzzy_clustering(monkeypatch)
    today = date.today()
    current_month_start = today.replace(day=1)

    descs = ["Olive Garden", "Sushi Place", "Burger Joint"]
    for i, month_offset in enumerate(range(1, 4)):
        d = current_month_start - timedelta(days=30 * month_offset)
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(date=str(d), description=descs[i], category="Dining", amount=100.00),
        )

    auth_client_a.post(
        "/api/expenses",
        json=make_expense(date=str(today), description="Fancy Anniversary Dinner", category="Dining", amount=200.00),
    )

    data = auth_client_a.get("/api/insights").json()
    trend_alerts = data["category_trend_alerts"]
    dining_alerts = [a for a in trend_alerts if a["category"] == "Dining"]
    assert len(dining_alerts) == 1
    assert dining_alerts[0]["direction"] == "up"
    assert dining_alerts[0]["change_pct"] > 25
    # Should include shared secondary fields
    assert "shared_current_month_amount" in dining_alerts[0]
    assert "shared_three_month_avg" in dining_alerts[0]


def test_category_trend_prorates_by_day_of_month():
    """Direct, exact-value check of the fix: MTD is compared against the
    median spend through the *same day-of-month* in the prior 3 months, not
    a full-month average. The bug this replaces: on the 12th you're only
    ~40% through the month, so a category on pace to nearly double its usual
    spend still reads "down" against a full-month baseline (150 vs 160 here)
    -- comparing prorated-to-prorated instead correctly reads it as "up".
    """
    from routes.insights import _category_trend_alerts

    frozen_today = date(2026, 3, 12)
    expenses = []
    exp_id = 1
    # Prior 3 months (Dec, Jan, Feb): $70 by the 12th, $160 by month end.
    for month in (12, 1, 2):
        year = 2025 if month == 12 else 2026
        for day, amt in ((5, "40.00"), (10, "30.00"), (20, "90.00")):
            expenses.append(Expense(
                id=exp_id, date=date(year, month, day), description=f"Dinner {year}-{month}-{day}",
                amount=Decimal(amt), category="Dining", paid_by=USER_A, split_method="Personal",
            ))
            exp_id += 1
    # Current month (March) MTD by the 12th: $150 -- more than double the
    # usual $70 pace, but nowhere near the $160 full-month average.
    for day, amt in ((5, "80.00"), (10, "70.00")):
        expenses.append(Expense(
            id=exp_id, date=date(2026, 3, day), description=f"Dinner current-{day}",
            amount=Decimal(amt), category="Dining", paid_by=USER_A, split_method="Personal",
        ))
        exp_id += 1

    alerts = _category_trend_alerts(expenses, USER_A, USER_B, anomalies=[], price_step_alerts=[], today=frozen_today)
    dining = next(a for a in alerts if a["category"] == "Dining")
    assert dining["current_month_amount"] == 150.0
    assert dining["three_month_avg"] == 70.0
    assert dining["three_month_full_avg"] == 160.0
    assert dining["change_pct"] == round((150.0 - 70.0) / 70.0 * 100, 1)
    assert dining["direction"] == "up"


def test_category_trend_attribution_suppresses_when_anomaly_explains_excess():
    """If a category's MTD excess is already explained by an anomaly this
    month, the trend alert must be suppressed -- one insight, not two, for
    the same root cause."""
    from routes.insights import _category_trend_alerts

    frozen_today = date(2026, 3, 12)
    expenses = []
    exp_id = 1
    for month in (12, 1, 2):
        year = 2025 if month == 12 else 2026
        expenses.append(Expense(
            id=exp_id, date=date(year, month, 5), description=f"Dinner {year}-{month}",
            amount=Decimal("50.00"), category="Dining", paid_by=USER_A, split_method="Personal",
        ))
        exp_id += 1
    expenses.append(Expense(
        id=exp_id, date=date(2026, 3, 5), description="Normal dinner",
        amount=Decimal("50.00"), category="Dining", paid_by=USER_A, split_method="Personal",
    ))
    exp_id += 1
    expenses.append(Expense(
        id=exp_id, date=date(2026, 3, 8), description="Huge one-off dinner",
        amount=Decimal("500.00"), category="Dining", paid_by=USER_A, split_method="Personal",
    ))

    anomalies = [{"category": "Dining", "date": "2026-03-08", "my_portion": 500.0}]
    alerts = _category_trend_alerts(expenses, USER_A, USER_B, anomalies=anomalies, price_step_alerts=[], today=frozen_today)
    assert not any(a["category"] == "Dining" for a in alerts)

    # Without the anomaly to attribute against, the identical spend WOULD
    # fire -- proving the suppression above is doing real work, not
    # vacuously true because the alert wouldn't have fired anyway.
    alerts_unattributed = _category_trend_alerts(expenses, USER_A, USER_B, anomalies=[], price_step_alerts=[], today=frozen_today)
    assert any(a["category"] == "Dining" for a in alerts_unattributed)


def test_category_trend_attribution_suppresses_when_price_step_explains_excess():
    """Same idea as the anomaly case, but attributed to a detected
    recurring price-step alert (item 2) instead."""
    from routes.insights import _category_trend_alerts

    frozen_today = date(2026, 3, 12)
    expenses = []
    exp_id = 1
    for month in (12, 1, 2):
        year = 2025 if month == 12 else 2026
        expenses.append(Expense(
            id=exp_id, date=date(year, month, 5), description=f"Bill {year}-{month}",
            amount=Decimal("50.00"), category="Dining", paid_by=USER_A, split_method="Personal",
        ))
        exp_id += 1
    expenses.append(Expense(
        id=exp_id, date=date(2026, 3, 5), description="Bill current",
        amount=Decimal("150.00"), category="Dining", paid_by=USER_A, split_method="Personal",
    ))

    price_step_alerts = [{"category": "Dining", "my_current_amount": 150.0, "my_previous_avg": 50.0}]
    alerts = _category_trend_alerts(expenses, USER_A, USER_B, anomalies=[], price_step_alerts=price_step_alerts, today=frozen_today)
    assert not any(a["category"] == "Dining" for a in alerts)

    alerts_unattributed = _category_trend_alerts(expenses, USER_A, USER_B, anomalies=[], price_step_alerts=[], today=frozen_today)
    assert any(a["category"] == "Dining" for a in alerts_unattributed)


# ── Forecast ───────────────────────────────────────────────────────────


def _month_ago(base: date, n: int) -> date:
    """n calendar months before base, same day-of-month (15th, always valid)."""
    y, m = base.year, base.month - n
    while m <= 0:
        m += 12
        y -= 1
    return date(y, m, 15)


def _no_fuzzy_clustering(monkeypatch):
    """Force exact-description-match only (no embedding-similarity
    merging), so a test can use several distinct one-off descriptions
    within one category and be certain none of them accidentally cluster
    into a 3+-occurrence "recurring" series -- deterministic regardless of
    the real embedding model's similarity scores (same rationale as
    test_suggestions.py's `cluster_descriptions` monkeypatch, bucket 08)."""
    import routes.insights as insights_mod
    monkeypatch.setattr(
        insights_mod, "cluster_descriptions_all",
        lambda descs, threshold=0.85: [[i] for i in range(len(descs))],
    )


def test_forecast_empty_db(auth_client_a):
    data = auth_client_a.get("/api/insights").json()
    forecast = data["forecast"]
    assert forecast["total_forecast"] == 0
    assert forecast["by_category"] == []
    assert forecast["scheduled_bills"] == []
    assert forecast["upcoming_bills"] == []
    assert forecast["range"] is None


def test_forecast_variable_uses_median_of_last_3_months(auth_client_a, monkeypatch):
    """Variable-category forecast = median of the last 3 complete calendar
    months (not a recency-weighted average) -- exact assertion, not `> 0`,
    per this bucket's own verification requirement. Distinct one-off
    descriptions so nothing here is mistaken for a recurring series (see
    test_forecast_recurring_bill_excluded_from_variable for that case)."""
    _no_fuzzy_clustering(monkeypatch)
    today = date.today()

    # Three calendar-month-aligned, unambiguous periods (1, 2, 3 months back).
    # Personal/paid-by-me so "my portion" is the full amount, same as the
    # shared total, keeping the arithmetic simple.
    amounts_by_offset = {1: 110.00, 2: 120.00, 3: 130.00}
    for month_offset, amount in amounts_by_offset.items():
        resp = auth_client_a.post(
            "/api/expenses",
            json=make_expense(
                date=str(_month_ago(today, month_offset)),
                description=f"Grocery run (month -{month_offset})",
                category="Groceries",
                amount=amount,
                paid_by=USER_A,
                split_method="Personal",
            ),
        )
        assert resp.status_code == 201

    data = auth_client_a.get("/api/insights").json()
    forecast = data["forecast"]

    # median(110, 120, 130) = 120; last complete month's actual is 110.
    assert forecast["recurring_total"] == 0
    assert forecast["variable_total"] == 120.0
    assert forecast["shared_variable_total"] == 120.0
    assert forecast["total_forecast"] == 120.0
    assert forecast["shared_total_forecast"] == 120.0
    assert forecast["last_month_total"] == 110.0
    assert forecast["change_vs_last_month_pct"] == round((120.0 - 110.0) / 110.0 * 100, 1)
    assert forecast["by_category"] == [{
        "category": "Groceries",
        "forecast": 120.0,
        "shared_forecast": 120.0,
        "last_month": 110.0,
        "shared_last_month": 110.0,
        "type": "variable",
    }]


def test_forecast_50_50_shows_user_portion(auth_client_a, monkeypatch):
    """50/50 expense of $100 should show exactly $50 in forecast — a flat
    $100/month for 3 straight months has one right answer, not a range.
    The old 45-55 band is exactly why the inverted-weights bug (weights
    applied to periods in the wrong order — see bucket 09) survived
    undetected: a wrong-but-plausible total still lands in a wide band."""
    _no_fuzzy_clustering(monkeypatch)
    today = date.today()

    for month_offset in (1, 2, 3):
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(
                date=str(_month_ago(today, month_offset)),
                description=f"Grocery run (month -{month_offset})",
                category="Groceries",
                amount=100.00,
                split_method="50/50",
                paid_by=USER_A,
            ),
        )

    data = auth_client_a.get("/api/insights").json()
    forecast = data["forecast"]
    assert forecast["total_forecast"] == 50.0
    assert forecast["shared_total_forecast"] == 100.0


def test_forecast_personal_other_excluded(auth_client_a, auth_client_b):
    """A recurring series paid entirely by the other user must show $0 in
    my forecast -- and, since it's detected as recurring (3 occurrences,
    ~30 days apart), it's also excluded entirely from the variable
    category total rather than merely zero-weighted."""
    today = date.today()
    current_month_start = today.replace(day=1)

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
    assert forecast["total_forecast"] == 0
    assert forecast["variable_total"] == 0
    assert forecast["recurring_total"] == 0


def test_forecast_recurring_bill_excluded_from_variable(auth_client_a):
    """A detected recurring bill's amount must not also show up in the
    variable by_category total for its category -- the old bug this bucket
    fixes double-counted (or mis-smeared) recurring spend into the
    category-wide rolling average."""
    today = date.today()
    for i in range(4):
        d = today - timedelta(days=30 * i)
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(
                date=str(d), description="Netflix", category="Subscription",
                amount=15.99, split_method="Personal", paid_by=USER_A,
            ),
        )

    data = auth_client_a.get("/api/insights").json()
    forecast = data["forecast"]
    subscription_row = next((c for c in forecast["by_category"] if c["category"] == "Subscription"), None)
    assert subscription_row is None
    assert forecast["recurring_summary"]["active_count"] == 1


def test_on_pace_mtd_actual_reflects_month_to_date_spend(auth_client_a):
    """'On pace' MTD actual is the true sum of this month's postings so
    far, independent of the target-month forecast."""
    today = date.today()
    current_month_start = today.replace(day=1)
    auth_client_a.post(
        "/api/expenses",
        json=make_expense(
            date=str(current_month_start), description="Groceries so far",
            category="Groceries", amount=80.00, split_method="Personal", paid_by=USER_A,
        ),
    )

    data = auth_client_a.get("/api/insights").json()
    on_pace = data["forecast"]["on_pace"]
    assert on_pace["month"] == today.strftime("%Y-%m")
    assert on_pace["mtd_actual"] == 80.0
    assert on_pace["shared_mtd_actual"] == 80.0


def test_recurring_summary_and_upcoming_bills(auth_client_a):
    """Subscription roll-up: active count + monthly/annual equivalent, and
    an upcoming-bills list sorted by next due date."""
    today = date.today()
    for i in range(4):
        d = today - timedelta(days=30 * i)
        auth_client_a.post(
            "/api/expenses",
            json=make_expense(
                date=str(d), description="Netflix", category="Subscription",
                amount=15.00, split_method="Personal", paid_by=USER_A,
            ),
        )

    data = auth_client_a.get("/api/insights").json()
    summary = data["forecast"]["recurring_summary"]
    assert summary["active_count"] == 1
    assert summary["monthly_equivalent"] == 15.0
    assert summary["annual_equivalent"] == 180.0

    upcoming = data["forecast"]["upcoming_bills"]
    assert len(upcoming) == 1
    assert upcoming[0]["description"] == "Netflix"
    assert upcoming[0]["status"] == "active"


def test_annual_bill_appears_only_in_its_due_month(auth_client_a):
    """Direct unit-level check (bypassing the API so `today` can be frozen
    precisely, independent of when this test happens to run): an annual
    series' scheduled amount must appear in the forecast only for the
    calendar month containing its projected due date, not the months
    before or after."""
    from routes.insights import _detect_recurring, _forecast

    expenses = [
        Expense(id=1, date=date(2023, 3, 15), description="Car Insurance", amount=Decimal("600.00"),
                category="Car Insurance", paid_by=USER_A, split_method="Personal"),
        Expense(id=2, date=date(2024, 3, 15), description="Car Insurance", amount=Decimal("600.00"),
                category="Car Insurance", paid_by=USER_A, split_method="Personal"),
        Expense(id=3, date=date(2025, 3, 15), description="Car Insurance", amount=Decimal("600.00"),
                category="Car Insurance", paid_by=USER_A, split_method="Personal"),
    ]

    # "Today" = Feb 1 2026 -> target month = March 2026, which contains the
    # projected next_due (2025-03-15 + ~365 days ~= 2026-03-15).
    frozen_today = date(2026, 2, 1)
    recurring, member_ids = _detect_recurring(expenses, USER_A, USER_B, today=frozen_today)
    car = next(r for r in recurring if r["description"] == "Car Insurance")
    assert car["frequency"] == "Annual"

    forecast_hit = _forecast(expenses, recurring, member_ids, USER_A, USER_B, today=frozen_today)
    assert forecast_hit["recurring_total"] == 600.0
    assert forecast_hit["scheduled_bills"] == [{
        "description": "Car Insurance",
        "category": "Car Insurance",
        "due_date": "2026-03-15",
        "amount": 600.0,
        "my_amount": 600.0,
    }]

    # A different "today" (April 2026) -> target month = May 2026, which
    # does NOT contain the annual due date -> the bill must not appear.
    frozen_today_2 = date(2026, 4, 1)
    recurring2, member_ids2 = _detect_recurring(expenses, USER_A, USER_B, today=frozen_today_2)
    forecast_miss = _forecast(expenses, recurring2, member_ids2, USER_A, USER_B, today=frozen_today_2)
    assert forecast_miss["recurring_total"] == 0
    assert forecast_miss["scheduled_bills"] == []


# ── Top growing categories ─────────────────────────────────────────────


def test_top_growing_categories(auth_client_a):
    """A category with increasing monthly spend should appear in top growing,
    with the exact growth rate and the exact per-month amounts — a bare
    `if growing: if ent: ...` would pass vacuously on an empty list, which is
    exactly what let a real bug in this code path go uncaught before."""
    today = date.today()

    # $50 -> $100 -> $150, three calendar months back to one month back.
    # Personal/paid-by-me so "my portion" equals the full amount, keeping
    # the expected numbers simple and unambiguous.
    amounts = [50, 100, 150]
    for i, month_offset in enumerate([3, 2, 1]):
        y, m = today.year, today.month - month_offset
        while m <= 0:
            m += 12
            y -= 1
        d = date(y, m, 15)
        resp = auth_client_a.post(
            "/api/expenses",
            json=make_expense(
                date=str(d),
                description="Entertainment",
                category="Entertainment",
                amount=amounts[i],
                paid_by=USER_A,
                split_method="Personal",
            ),
        )
        assert resp.status_code == 201

    data = auth_client_a.get("/api/insights").json()
    growing = data["top_growing_categories"]
    ent = next((g for g in growing if g["category"] == "Entertainment"), None)
    assert ent is not None, f"Entertainment missing from top_growing_categories: {growing}"

    # Month-over-month growth: 50->100 is +100%, 100->150 is +50%; average 75%.
    assert ent["avg_mom_growth_pct"] == 75.0
    assert ent["last_3_months"] == [50.0, 100.0, 150.0]
    assert ent["shared_last_3_months"] == [50.0, 100.0, 150.0]


# ── Personal mode ─────────────────────────────────────────────────────


def test_personal_mode_insights(auth_client_a, db):
    """In personal mode, all amounts should be at 100% (no splitting)."""
    set_mode(db, "personal")
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
    assert data["mode"] == "personal"

    ww = data["weekend_vs_weekday"]
    # In personal mode, your expense == shared expense == full amount
    assert ww["your_expense"]["weekend"]["total"] == 100.0
    assert ww["shared_expense"]["weekend"]["total"] == 100.0


# ── Income insights ───────────────────────────────────────────────────


def test_income_insights_none_shared(auth_client_a):
    """In shared mode, income_insights should be None."""
    data = auth_client_a.get("/api/insights").json()
    assert data["income_insights"] is None


def test_income_insights_present_blended(auth_client_a, db):
    """In blended mode with income data, income_insights should be populated."""
    set_mode(db, "blended")
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
    set_mode(db, "blended")
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
    """In blended mode with no income entries, income_insights should be None."""
    set_mode(db, "blended")
    data = auth_client_a.get("/api/insights").json()
    assert data["income_insights"] is None


def test_income_insights_by_source(auth_client_a, db):
    """Income by source should break down correctly."""
    set_mode(db, "blended")
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
    set_mode(db, "blended")
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
