"""
Smart Insights endpoint.

Computes recurring payments, spending habits, category trends,
anomalies, forecasts, and growth rankings — all from expense history.
All monetary values are computed for the current user's portion where applicable.
"""

import statistics
from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlmodel import Session, select

from auth import get_current_user
from config import get_app_mode
from database import get_session
from models import Expense, Income
from routes.expenses import _resolve_names
from services.clustering import cluster_descriptions_all

router = APIRouter()

EXCLUDED_CATEGORIES = {"Payment", "Reimbursement"}


def _dec(val) -> Decimal:
    return Decimal(str(val)) if val else Decimal("0")


def _month_key(d: date) -> str:
    return d.strftime("%Y-%m")


def _months_back(d: date, n: int) -> date:
    """Return the date exactly n calendar months before d, clamping to month-end."""
    total = d.year * 12 + (d.month - 1) - n
    year, month = total // 12, total % 12 + 1
    return date(year, month, min(d.day, monthrange(year, month)[1]))


# ── Helpers ────────────────────────────────────────────────────────────


def _my_portion(e: Expense, me: str, other: str) -> float:
    """Compute the current user's portion of an expense (Python mirror of SQL _my_portion_expr)."""
    amt = float(e.amount)
    if e.split_method == "Personal":
        return amt if e.paid_by == me else 0.0
    if e.split_method == "50/50":
        return amt / 2
    if e.split_method == f"100% {me}":
        return amt
    if e.split_method == f"100% {other}":
        return 0.0
    return 0.0


def _fetch_all_expenses(session: Session) -> list[Expense]:
    """Fetch all non-Payment/Reimbursement expenses ordered by date."""
    stmt = (
        select(Expense)
        .where(Expense.category.notin_(EXCLUDED_CATEGORIES))
        .order_by(Expense.date.asc(), Expense.id.asc())
    )
    return list(session.exec(stmt).all())


def _detect_recurring(expenses: list[Expense], me: str, other: str) -> list[dict[str, Any]]:
    """Detect recurring expenses by clustering descriptions and analyzing intervals.

    Returns a list of recurring expense groups with frequency classification.
    """
    if not expenses:
        return []

    # Group expenses by description (exact match first, then cluster)
    desc_map: dict[str, list[Expense]] = defaultdict(list)
    for e in expenses:
        desc_map[e.description].append(e)

    # Get unique descriptions
    unique_descs = list(desc_map.keys())
    if not unique_descs:
        return []

    # Cluster similar descriptions
    try:
        clusters = cluster_descriptions_all(unique_descs, threshold=0.85)
    except Exception:
        # If embedding fails, fall back to exact match only
        clusters = [[i] for i in range(len(unique_descs))]

    recurring = []
    for cluster_indices in clusters:
        # Gather all expenses in this cluster
        cluster_expenses: list[Expense] = []
        cluster_descs = [unique_descs[i] for i in cluster_indices]
        for desc in cluster_descs:
            cluster_expenses.extend(desc_map[desc])

        if len(cluster_expenses) < 3:
            continue

        # Sort by date
        cluster_expenses.sort(key=lambda e: (e.date, e.id))

        # Use the most frequent description as canonical name
        desc_counts: dict[str, int] = defaultdict(int)
        for e in cluster_expenses:
            desc_counts[e.description] += 1
        canonical = max(desc_counts, key=lambda d: desc_counts[d])

        # Most common category
        cat_counts: dict[str, int] = defaultdict(int)
        for e in cluster_expenses:
            cat_counts[e.category] += 1
        category = max(cat_counts, key=lambda c: cat_counts[c])

        # Compute intervals between consecutive occurrences (in days)
        dates = [e.date for e in cluster_expenses]
        intervals = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]

        if not intervals:
            continue

        median_interval = statistics.median(intervals)

        # Classify frequency by median interval
        frequency = _classify_frequency(median_interval)
        if not frequency:
            continue

        # Check interval consistency (coefficient of variation < 0.5)
        if len(intervals) >= 2:
            try:
                mean_interval = statistics.mean(intervals)
                stdev_interval = statistics.stdev(intervals)
                if mean_interval > 0 and (stdev_interval / mean_interval) > 0.5:
                    continue
            except statistics.StatisticsError:
                continue

        amounts = [float(e.amount) for e in cluster_expenses]
        avg_amount = round(statistics.mean(amounts), 2)
        last_expense = cluster_expenses[-1]

        my_amounts = [_my_portion(e, me, other) for e in cluster_expenses]
        avg_my_amount = round(statistics.mean(my_amounts), 2)

        recurring.append({
            "description": canonical,
            "category": category,
            "frequency": frequency,
            "avg_amount": avg_amount,
            "last_amount": float(last_expense.amount),
            "avg_my_amount": avg_my_amount,
            "last_my_amount": round(_my_portion(last_expense, me, other), 2),
            "last_date": str(last_expense.date),
            "occurrence_count": len(cluster_expenses),
            "median_interval_days": round(median_interval, 1),
        })

    # Sort by frequency importance: weekly > biweekly > monthly > quarterly > annual
    freq_order = {"Weekly": 0, "Biweekly": 1, "Monthly": 2, "Quarterly": 3, "Annual": 4}
    recurring.sort(key=lambda r: (freq_order.get(r["frequency"], 99), -r["avg_amount"]))
    return recurring


def _classify_frequency(median_interval: float) -> str | None:
    """Classify recurrence frequency from median interval in days."""
    if 5 <= median_interval <= 9:
        return "Weekly"
    elif 10 <= median_interval <= 18:
        return "Biweekly"
    elif 25 <= median_interval <= 35:
        return "Monthly"
    elif 80 <= median_interval <= 100:
        return "Quarterly"
    elif 340 <= median_interval <= 400:
        return "Annual"
    return None


def _detect_recurring_alerts(recurring: list[dict]) -> list[dict[str, Any]]:
    """Generate alerts when recurring payment amounts change significantly (>15%)."""
    alerts = []
    for item in recurring:
        if item["occurrence_count"] < 3:
            continue
        avg = item["avg_amount"]
        last = item["last_amount"]
        if avg == 0:
            continue
        change_pct = round(((last - avg) / abs(avg)) * 100, 1)
        if abs(change_pct) > 15:
            alerts.append({
                "description": item["description"],
                "category": item["category"],
                "previous_avg": avg,
                "current_amount": last,
                "my_previous_avg": item.get("avg_my_amount", avg),
                "my_current_amount": item.get("last_my_amount", last),
                "change_pct": change_pct,
                "direction": "up" if change_pct > 0 else "down",
            })
    return alerts


def _weekend_vs_weekday(expenses: list[Expense], me: str, other: str) -> dict[str, Any]:
    """Split spending into weekend vs weekday with per-category breakdowns.

    Returns dual view: your_expense (user's portion) and shared_expense (full amounts).
    """
    # Shared (full amount) accumulators
    s_weekday_total = 0.0
    s_weekend_total = 0.0
    weekday_count = 0
    weekend_count = 0
    s_weekday_cats: dict[str, float] = defaultdict(float)
    s_weekend_cats: dict[str, float] = defaultdict(float)

    # Your portion accumulators
    y_weekday_total = 0.0
    y_weekend_total = 0.0
    y_weekday_cats: dict[str, float] = defaultdict(float)
    y_weekend_cats: dict[str, float] = defaultdict(float)

    for e in expenses:
        amt = float(e.amount)
        my_amt = _my_portion(e, me, other)
        is_weekend = e.date.weekday() >= 5  # Saturday=5, Sunday=6

        if is_weekend:
            s_weekend_total += amt
            weekend_count += 1
            s_weekend_cats[e.category] += amt
            y_weekend_total += my_amt
            y_weekend_cats[e.category] += my_amt
        else:
            s_weekday_total += amt
            weekday_count += 1
            s_weekday_cats[e.category] += amt
            y_weekday_total += my_amt
            y_weekday_cats[e.category] += my_amt

    def _cat_list(cats: dict[str, float]) -> list[dict]:
        return sorted(
            [{"category": c, "amount": round(a, 2)} for c, a in cats.items() if a > 0],
            key=lambda x: -x["amount"],
        )

    return {
        "your_expense": {
            "weekday": {
                "total": round(y_weekday_total, 2),
                "count": weekday_count,
                "by_category": _cat_list(y_weekday_cats),
            },
            "weekend": {
                "total": round(y_weekend_total, 2),
                "count": weekend_count,
                "by_category": _cat_list(y_weekend_cats),
            },
        },
        "shared_expense": {
            "weekday": {
                "total": round(s_weekday_total, 2),
                "count": weekday_count,
                "by_category": _cat_list(s_weekday_cats),
            },
            "weekend": {
                "total": round(s_weekend_total, 2),
                "count": weekend_count,
                "by_category": _cat_list(s_weekend_cats),
            },
        },
    }


def _category_trend_alerts(expenses: list[Expense], me: str, other: str) -> list[dict[str, Any]]:
    """Alert when a category's current month spend deviates >25% from 3-month average.

    Uses the user's portion for trend detection; includes shared amounts as secondary.
    """
    today = date.today()
    current_month = _month_key(today)

    # Build per-category monthly totals for last 4 months
    four_months_ago = (today.replace(day=1) - timedelta(days=92)).replace(day=1)
    recent = [e for e in expenses if e.date >= four_months_ago]

    cat_months_my: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    cat_months_shared: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for e in recent:
        mk = _month_key(e.date)
        cat_months_my[e.category][mk] += _my_portion(e, me, other)
        cat_months_shared[e.category][mk] += float(e.amount)

    # Get the last 3 complete months (excluding current)
    months_set: set[str] = set()
    for cats in cat_months_my.values():
        months_set.update(cats.keys())
    past_months = sorted(m for m in months_set if m < current_month)[-3:]

    if not past_months:
        return []

    alerts = []
    for category, monthly in cat_months_my.items():
        current_spend = monthly.get(current_month, 0)
        past_spends = [monthly.get(m, 0) for m in past_months]
        past_avg = statistics.mean(past_spends) if past_spends else 0

        if past_avg < 10:  # Skip negligible categories
            continue

        if current_spend == 0:
            continue

        change_pct = round(((current_spend - past_avg) / abs(past_avg)) * 100, 1)
        if abs(change_pct) > 25:
            shared_monthly = cat_months_shared.get(category, {})
            alerts.append({
                "category": category,
                "current_month_amount": round(current_spend, 2),
                "three_month_avg": round(past_avg, 2),
                "shared_current_month_amount": round(shared_monthly.get(current_month, 0), 2),
                "shared_three_month_avg": round(
                    statistics.mean([shared_monthly.get(m, 0) for m in past_months]), 2
                ),
                "change_pct": change_pct,
                "direction": "up" if change_pct > 0 else "down",
            })

    alerts.sort(key=lambda a: -abs(a["change_pct"]))
    return alerts


def _detect_anomalies(expenses: list[Expense], me: str, other: str) -> list[dict[str, Any]]:
    """Flag recent expenses with unusually high/low amounts per category (z-score > 2).

    Z-score detection runs on full amounts; each anomaly includes the user's portion.
    """
    today = date.today()
    cutoff = today - timedelta(days=60)

    # Group all amounts by category
    cat_amounts: dict[str, list[float]] = defaultdict(list)
    for e in expenses:
        cat_amounts[e.category].append(float(e.amount))

    anomalies = []
    for e in expenses:
        if e.date < cutoff:
            continue

        amounts = cat_amounts.get(e.category, [])
        if len(amounts) < 5:
            continue

        mean = statistics.mean(amounts)
        try:
            stdev = statistics.stdev(amounts)
        except statistics.StatisticsError:
            continue

        if stdev == 0:
            continue

        z_score = (float(e.amount) - mean) / stdev
        if abs(z_score) > 2:
            anomalies.append({
                "id": e.id,
                "description": e.description,
                "category": e.category,
                "amount": float(e.amount),
                "my_portion": round(_my_portion(e, me, other), 2),
                "date": str(e.date),
                "paid_by": e.paid_by,
                "category_mean": round(mean, 2),
                "category_std": round(stdev, 2),
                "z_score": round(z_score, 1),
                "direction": "high" if z_score > 0 else "low",
            })

    anomalies.sort(key=lambda a: -abs(a["z_score"]))
    return anomalies


def _forecast(
    expenses: list[Expense],
    recurring: list[dict],
    me: str,
    other: str,
) -> dict[str, Any]:
    """Project next month spending using recurring expenses + weighted moving average.

    Anchors to the last expense date and uses 3 rolling ~monthly windows working
    backward from there, so partially-entered recent months don't distort weights.
    Weights: 50% period-1 (most recent), 30% period-2, 20% period-3.
    Computes user's portion as primary, shared (full) amounts as secondary.
    """
    _empty: dict[str, Any] = {
        "recurring_total": 0,
        "variable_total": 0,
        "total_forecast": 0,
        "last_month_total": 0,
        "change_vs_last_month_pct": 0,
        "shared_total_forecast": 0,
        "by_category": [],
    }

    if not expenses:
        return _empty

    # Anchor rolling windows to the last entered expense date.
    # bounds[k] < date <= bounds[k-1]  →  period k  (k = 1, 2, 3)
    anchor = max(e.date for e in expenses)
    bounds = [anchor] + [_months_back(anchor, i) for i in range(1, 4)]

    # Dual accumulation: user's portion and shared (full) amounts
    cat_periods_mine: dict[str, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    cat_periods_shared: dict[str, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    for e in expenses:
        for k in range(1, 4):
            if bounds[k] < e.date <= bounds[k - 1]:
                cat_periods_mine[e.category][k] += _my_portion(e, me, other)
                cat_periods_shared[e.category][k] += float(e.amount)
                break

    # Use shared periods to determine data availability (a user with 0 portion
    # of some expenses should still see that period exists)
    periods_with_data = sorted(
        {p for cats in cat_periods_shared.values() for p in cats},
        reverse=True,
    )[:3]

    if not periods_with_data:
        return _empty

    weights_map = {1: [1.0], 2: [0.6, 0.4], 3: [0.5, 0.3, 0.2]}
    weights = weights_map.get(len(periods_with_data), [0.5, 0.3, 0.2])
    ordered_periods = periods_with_data

    recurring_total = 0.0
    variable_total = 0.0
    shared_recurring_total = 0.0
    shared_variable_total = 0.0
    by_category = []

    most_recent_period = ordered_periods[0]
    last_month_total = 0.0
    shared_last_month_total = 0.0

    # Iterate over all categories that have data in either view
    all_categories = set(cat_periods_mine.keys()) | set(cat_periods_shared.keys())
    for category in all_categories:
        my_period_amounts = cat_periods_mine.get(category, {})
        shared_period_amounts = cat_periods_shared.get(category, {})

        last_month_total += my_period_amounts.get(most_recent_period, 0)
        shared_last_month_total += shared_period_amounts.get(most_recent_period, 0)

        # Weighted average across rolling periods
        my_amounts = [my_period_amounts.get(p, 0) for p in ordered_periods]
        forecast_amount = sum(a * w for a, w in zip(my_amounts, weights))

        shared_amounts = [shared_period_amounts.get(p, 0) for p in ordered_periods]
        shared_forecast_amount = sum(a * w for a, w in zip(shared_amounts, weights))

        is_recurring = category.lower() in [r["category"].lower() for r in recurring]

        if is_recurring:
            recurring_total += forecast_amount
            shared_recurring_total += shared_forecast_amount
        else:
            variable_total += forecast_amount
            shared_variable_total += shared_forecast_amount

        by_category.append({
            "category": category,
            "forecast": round(forecast_amount, 2),
            "last_month": round(my_period_amounts.get(most_recent_period, 0), 2),
            "shared_forecast": round(shared_forecast_amount, 2),
            "shared_last_month": round(shared_period_amounts.get(most_recent_period, 0), 2),
            "type": "recurring" if is_recurring else "variable",
        })

    total_forecast = round(recurring_total + variable_total, 2)
    shared_total_forecast = round(shared_recurring_total + shared_variable_total, 2)
    change_pct = (
        round(((total_forecast - last_month_total) / last_month_total) * 100, 1)
        if last_month_total > 0
        else 0
    )

    by_category.sort(key=lambda x: -x["forecast"])

    return {
        "recurring_total": round(recurring_total, 2),
        "variable_total": round(variable_total, 2),
        "total_forecast": total_forecast,
        "last_month_total": round(last_month_total, 2),
        "change_vs_last_month_pct": change_pct,
        "shared_total_forecast": shared_total_forecast,
        "by_category": by_category,
    }


def _top_growing_categories(expenses: list[Expense], me: str, other: str) -> list[dict[str, Any]]:
    """Rank categories by average month-over-month growth rate over last 3 months.

    Uses the user's portion for growth calculation; includes shared values as secondary.
    """
    today = date.today()
    current_month = _month_key(today)
    three_months_ago = (today.replace(day=1) - timedelta(days=92)).replace(day=1)

    recent = [e for e in expenses if e.date >= three_months_ago]

    cat_months_my: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    cat_months_shared: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for e in recent:
        mk = _month_key(e.date)
        cat_months_my[e.category][mk] += _my_portion(e, me, other)
        cat_months_shared[e.category][mk] += float(e.amount)

    months_set: set[str] = set()
    for cats in cat_months_my.values():
        months_set.update(cats.keys())
    past_months = sorted(m for m in months_set if m < current_month)[-3:]

    if len(past_months) < 2:
        return []

    results = []
    for category, monthly in cat_months_my.items():
        month_values = [monthly.get(m, 0) for m in past_months]

        if any(v < 10 for v in month_values):
            continue

        growth_rates = []
        for i in range(1, len(month_values)):
            prev = month_values[i - 1]
            curr = month_values[i]
            if prev > 0:
                growth_rates.append(((curr - prev) / prev) * 100)

        if not growth_rates:
            continue

        avg_growth = round(statistics.mean(growth_rates), 1)
        shared_monthly = cat_months_shared.get(category, {})
        results.append({
            "category": category,
            "avg_mom_growth_pct": avg_growth,
            "last_3_months": [round(v, 2) for v in month_values],
            "shared_last_3_months": [round(shared_monthly.get(m, 0), 2) for m in past_months],
            "months": past_months,
        })

    results.sort(key=lambda x: -x["avg_mom_growth_pct"])
    return results[:5]


# ── Income insights ───────────────────────────────────────────────────


def _income_insights(
    session: Session,
    current_user: str,
    me: str,
    other: str,
    expenses: list[Expense],
) -> dict[str, Any] | None:
    """Compute income-based insights: savings rate, income vs expense, and income by source.

    Returns None if no income data exists.
    """
    incomes = list(
        session.exec(
            select(Income)
            .where(Income.user_id == current_user)
            .order_by(Income.date.asc())
        ).all()
    )
    if not incomes:
        return None

    today = date.today()

    # Build monthly income by source and total
    income_by_month: dict[str, float] = defaultdict(float)
    income_by_month_source: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for inc in incomes:
        mk = _month_key(inc.date)
        income_by_month[mk] += float(inc.amount)
        income_by_month_source[mk][inc.source] += float(inc.amount)

    # Build monthly expense totals (user's portion)
    expense_by_month: dict[str, float] = defaultdict(float)
    for e in expenses:
        expense_by_month[_month_key(e.date)] += _my_portion(e, me, other)

    # Determine last 6 months (including current)
    months = []
    for i in range(6):
        d = _months_back(today, i)
        months.append(_month_key(d))
    months.reverse()  # oldest first

    # Savings rate trend
    savings_trend = []
    for m in months:
        inc = round(income_by_month.get(m, 0), 2)
        exp = round(expense_by_month.get(m, 0), 2)
        savings = round(inc - exp, 2)
        rate_pct = round((savings / inc) * 100, 1) if inc > 0 else 0
        savings_trend.append({
            "month": m,
            "income": inc,
            "expenses": exp,
            "savings": savings,
            "rate_pct": rate_pct,
        })

    current_month_key = _month_key(today)
    current_entry = next((s for s in savings_trend if s["month"] == current_month_key), None)

    # Income vs expense monthly comparison
    income_vs_expense = []
    for m in months:
        inc = round(income_by_month.get(m, 0), 2)
        exp = round(expense_by_month.get(m, 0), 2)
        income_vs_expense.append({
            "month": m,
            "income": inc,
            "expense": exp,
            "surplus": round(inc - exp, 2),
        })

    # Income by source: current month + trend
    all_sources = set()
    for sources in income_by_month_source.values():
        all_sources.update(sources.keys())

    current_by_source = [
        {"source": s, "amount": round(income_by_month_source.get(current_month_key, {}).get(s, 0), 2)}
        for s in sorted(all_sources)
    ]

    source_trend = []
    for m in months:
        sources_data = income_by_month_source.get(m, {})
        source_trend.append({
            "month": m,
            "sources": [
                {"source": s, "amount": round(sources_data.get(s, 0), 2)}
                for s in sorted(all_sources)
            ],
        })

    return {
        "savings_rate": {
            "current_month": current_entry or {
                "month": current_month_key, "income": 0, "expenses": 0,
                "savings": 0, "rate_pct": 0,
            },
            "trend": savings_trend,
        },
        "income_vs_expense": {
            "monthly": income_vs_expense,
        },
        "income_by_source": {
            "current_month": current_by_source,
            "trend": source_trend,
        },
    }


# ── Main endpoint ──────────────────────────────────────────────────────


@router.get("/insights")
def get_insights(
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    """Return all smart insights in a single response.

    All monetary amounts reflect the current user's portion of each expense.
    """
    mode = get_app_mode(session)
    me, other = _resolve_names(current_user, session)
    expenses = _fetch_all_expenses(session)

    # A: Recurring payment detection
    recurring = _detect_recurring(expenses, me, other)

    # B: Recurring change alerts
    recurring_alerts = _detect_recurring_alerts(recurring)

    # C: Weekend vs weekday spending (dual view: your + shared)
    weekend_weekday = _weekend_vs_weekday(expenses, me, other)

    # D: Category trend alerts (user-portion based)
    category_trends = _category_trend_alerts(expenses, me, other)

    # E: Expense anomalies (z-score on full amounts, portion included)
    anomalies = _detect_anomalies(expenses, me, other)

    # F: Next month forecast (user's portion)
    forecast = _forecast(expenses, recurring, me, other)

    # G: Top growing categories (user's portion)
    top_growing = _top_growing_categories(expenses, me, other)

    # H: Income insights (only for solo/hybrid modes)
    income_data = None
    if mode in ("personal", "blended"):
        income_data = _income_insights(session, current_user, me, other, expenses)

    return {
        "recurring_expenses": recurring,
        "recurring_alerts": recurring_alerts,
        "weekend_vs_weekday": weekend_weekday,
        "category_trend_alerts": category_trends,
        "anomalies": anomalies,
        "forecast": forecast,
        "top_growing_categories": top_growing,
        "income_insights": income_data,
        "mode": mode,
    }
