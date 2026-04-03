"""
Smart Insights endpoint.

Computes recurring payments, spending habits, category trends,
anomalies, forecasts, and growth rankings — all from expense history.
"""

import statistics
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlmodel import Session, select

from auth import get_current_user
from database import get_session
from models import Expense
from services.clustering import cluster_descriptions_all

router = APIRouter()

EXCLUDED_CATEGORIES = {"Payment", "Reimbursement"}


def _dec(val) -> Decimal:
    return Decimal(str(val)) if val else Decimal("0")


def _month_key(d: date) -> str:
    return d.strftime("%Y-%m")


# ── Helpers ────────────────────────────────────────────────────────────


def _fetch_all_expenses(session: Session) -> list[Expense]:
    """Fetch all non-Payment/Reimbursement expenses ordered by date."""
    stmt = (
        select(Expense)
        .where(Expense.category.notin_(EXCLUDED_CATEGORIES))
        .order_by(Expense.date.asc(), Expense.id.asc())
    )
    return list(session.exec(stmt).all())


def _detect_recurring(expenses: list[Expense]) -> list[dict[str, Any]]:
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

        recurring.append({
            "description": canonical,
            "category": category,
            "frequency": frequency,
            "avg_amount": avg_amount,
            "last_amount": float(last_expense.amount),
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
                "change_pct": change_pct,
                "direction": "up" if change_pct > 0 else "down",
            })
    return alerts


def _weekend_vs_weekday(expenses: list[Expense]) -> dict[str, Any]:
    """Split spending into weekend vs weekday with per-category breakdowns."""
    weekday_total = 0.0
    weekend_total = 0.0
    weekday_count = 0
    weekend_count = 0
    weekday_cats: dict[str, float] = defaultdict(float)
    weekend_cats: dict[str, float] = defaultdict(float)

    for e in expenses:
        amt = float(e.amount)
        if e.date.weekday() >= 5:  # Saturday=5, Sunday=6
            weekend_total += amt
            weekend_count += 1
            weekend_cats[e.category] += amt
        else:
            weekday_total += amt
            weekday_count += 1
            weekday_cats[e.category] += amt

    def _cat_list(cats: dict[str, float]) -> list[dict]:
        return sorted(
            [{"category": c, "amount": round(a, 2)} for c, a in cats.items()],
            key=lambda x: -x["amount"],
        )

    return {
        "weekday": {
            "total": round(weekday_total, 2),
            "count": weekday_count,
            "by_category": _cat_list(weekday_cats),
        },
        "weekend": {
            "total": round(weekend_total, 2),
            "count": weekend_count,
            "by_category": _cat_list(weekend_cats),
        },
    }


def _category_trend_alerts(expenses: list[Expense]) -> list[dict[str, Any]]:
    """Alert when a category's current month spend deviates >25% from 3-month average."""
    today = date.today()
    current_month = _month_key(today)

    # Build per-category monthly totals for last 4 months
    four_months_ago = (today.replace(day=1) - timedelta(days=92)).replace(day=1)
    recent = [e for e in expenses if e.date >= four_months_ago]

    cat_months: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for e in recent:
        cat_months[e.category][_month_key(e.date)] += float(e.amount)

    # Get the last 3 complete months (excluding current)
    months_set: set[str] = set()
    for cats in cat_months.values():
        months_set.update(cats.keys())
    past_months = sorted(m for m in months_set if m < current_month)[-3:]

    if not past_months:
        return []

    alerts = []
    for category, monthly in cat_months.items():
        current_spend = monthly.get(current_month, 0)
        past_spends = [monthly.get(m, 0) for m in past_months]
        past_avg = statistics.mean(past_spends) if past_spends else 0

        if past_avg < 10:  # Skip negligible categories
            continue

        if current_spend == 0:
            continue

        change_pct = round(((current_spend - past_avg) / abs(past_avg)) * 100, 1)
        if abs(change_pct) > 25:
            alerts.append({
                "category": category,
                "current_month_amount": round(current_spend, 2),
                "three_month_avg": round(past_avg, 2),
                "change_pct": change_pct,
                "direction": "up" if change_pct > 0 else "down",
            })

    alerts.sort(key=lambda a: -abs(a["change_pct"]))
    return alerts


def _detect_anomalies(expenses: list[Expense]) -> list[dict[str, Any]]:
    """Flag recent expenses with unusually high/low amounts per category (z-score > 2)."""
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
) -> dict[str, Any]:
    """Project next month spending using recurring expenses + weighted moving average.

    Weights: 50% last month, 30% two months ago, 20% three months ago.
    """
    today = date.today()
    current_month = _month_key(today)

    # Get last 3 complete months
    three_months_ago = (today.replace(day=1) - timedelta(days=92)).replace(day=1)
    recent = [e for e in expenses if e.date >= three_months_ago]

    cat_months: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for e in recent:
        cat_months[e.category][_month_key(e.date)] += float(e.amount)

    months_set: set[str] = set()
    for cats in cat_months.values():
        months_set.update(cats.keys())
    past_months = sorted(m for m in months_set if m < current_month)[-3:]

    if not past_months:
        return {
            "recurring_total": 0,
            "variable_total": 0,
            "total_forecast": 0,
            "last_month_total": 0,
            "change_vs_last_month_pct": 0,
            "by_category": [],
        }

    # Identify recurring description names
    recurring_descs = {r["description"].lower() for r in recurring}

    # Weights for the available months (most recent gets highest weight)
    weights_map = {1: [1.0], 2: [0.6, 0.4], 3: [0.5, 0.3, 0.2]}
    weights = weights_map.get(len(past_months), [0.5, 0.3, 0.2])

    # Reverse so index 0 = most recent month
    ordered_months = list(reversed(past_months))

    recurring_total = 0.0
    variable_total = 0.0
    by_category = []

    last_month = ordered_months[0] if ordered_months else None
    last_month_total = 0.0

    for category, monthly in cat_months.items():
        if last_month:
            last_month_total += monthly.get(last_month, 0)

        # Weighted average of past months
        month_amounts = [monthly.get(m, 0) for m in ordered_months]
        forecast_amount = sum(a * w for a, w in zip(month_amounts, weights))

        # Determine if category is primarily recurring
        is_recurring = category.lower() in [r["category"].lower() for r in recurring]

        if is_recurring:
            recurring_total += forecast_amount
        else:
            variable_total += forecast_amount

        by_category.append({
            "category": category,
            "forecast": round(forecast_amount, 2),
            "last_month": round(monthly.get(last_month, 0) if last_month else 0, 2),
            "type": "recurring" if is_recurring else "variable",
        })

    total_forecast = round(recurring_total + variable_total, 2)
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
        "by_category": by_category,
    }


def _top_growing_categories(expenses: list[Expense]) -> list[dict[str, Any]]:
    """Rank categories by average month-over-month growth rate over last 3 months."""
    today = date.today()
    current_month = _month_key(today)
    three_months_ago = (today.replace(day=1) - timedelta(days=92)).replace(day=1)

    recent = [e for e in expenses if e.date >= three_months_ago]

    cat_months: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for e in recent:
        cat_months[e.category][_month_key(e.date)] += float(e.amount)

    months_set: set[str] = set()
    for cats in cat_months.values():
        months_set.update(cats.keys())
    past_months = sorted(m for m in months_set if m < current_month)[-3:]

    if len(past_months) < 2:
        return []

    results = []
    for category, monthly in cat_months.items():
        month_values = [monthly.get(m, 0) for m in past_months]

        # Require minimum spend in all months
        if any(v < 10 for v in month_values):
            continue

        # Compute month-over-month growth rates
        growth_rates = []
        for i in range(1, len(month_values)):
            prev = month_values[i - 1]
            curr = month_values[i]
            if prev > 0:
                growth_rates.append(((curr - prev) / prev) * 100)

        if not growth_rates:
            continue

        avg_growth = round(statistics.mean(growth_rates), 1)
        results.append({
            "category": category,
            "avg_mom_growth_pct": avg_growth,
            "last_3_months": [round(v, 2) for v in month_values],
            "months": past_months,
        })

    results.sort(key=lambda x: -x["avg_mom_growth_pct"])
    return results[:5]


# ── Main endpoint ──────────────────────────────────────────────────────


@router.get("/insights")
def get_insights(
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    """Return all smart insights in a single response."""
    expenses = _fetch_all_expenses(session)

    # A: Recurring payment detection
    recurring = _detect_recurring(expenses)

    # B: Recurring change alerts
    recurring_alerts = _detect_recurring_alerts(recurring)

    # C: Weekend vs weekday spending
    weekend_weekday = _weekend_vs_weekday(expenses)

    # D: Category trend alerts
    category_trends = _category_trend_alerts(expenses)

    # E: Expense anomalies
    anomalies = _detect_anomalies(expenses)

    # F: Next month forecast
    forecast = _forecast(expenses, recurring)

    # G: Top growing categories
    top_growing = _top_growing_categories(expenses)

    return {
        "recurring_expenses": recurring,
        "recurring_alerts": recurring_alerts,
        "weekend_vs_weekday": weekend_weekday,
        "category_trend_alerts": category_trends,
        "anomalies": anomalies,
        "forecast": forecast,
        "top_growing_categories": top_growing,
    }
