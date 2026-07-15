"""
Smart Insights endpoint.

Computes recurring payments, spending habits, category trends,
anomalies, forecasts, and growth rankings — all from expense history.
All monetary values are computed for the current user's portion where applicable.
"""

import math
import statistics
from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import Session, select

from auth import get_current_user
from config import get_app_mode
from database import get_session
from models import Expense, Income
from services import alert_state
from services.audit import audit_logger
from services.clustering import cluster_descriptions_all
from services.insights_cache import get as _cache_get, put as _cache_put
from users import resolve_names
router = APIRouter()

EXCLUDED_CATEGORIES = {"Payment", "Reimbursement"}


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


# Canonical period grid (days). Replaces the old fixed-band classifier, whose
# dead zones at 19-24/36-79/101-339 days meant a bimonthly utility or
# semi-annual premium could never be detected.
PERIOD_GRID: list[tuple[float, str]] = [
    (7, "Weekly"),
    (14, "Biweekly"),
    (30.44, "Monthly"),
    (60.9, "Bimonthly"),
    (91.3, "Quarterly"),
    (182.6, "Semiannual"),
    (365.25, "Annual"),
]
FREQUENCY_ORDER = {label: i for i, (_, label) in enumerate(PERIOD_GRID)}

PERIOD_TOLERANCE = 0.2  # +/-20% of k * period counts as a match
PERIOD_CONFORMANCE_THRESHOLD = 0.6  # >=60% of intervals must match
BILL_RELATIVE_MAD_THRESHOLD = 0.05  # relative MAD below this reads as a fixed-price bill


def _score_period(intervals: list[int], period: float) -> tuple[float, float]:
    """Fraction of `intervals` explained by some small-integer multiple of
    `period` within +/-20%, plus the average multiple used.

    The average multiple (avg_k) is a tie-break signal: a run of 30-day gaps
    also "fits" a 7-day period at k=4, but the true period is whichever
    hypothesis needs the smallest, most-natural k (see _classify_period).
    """
    if not intervals:
        return 0.0, 99.0
    hits = 0
    ks = []
    for d in intervals:
        if d <= 0:
            continue
        k = max(1, round(d / period))
        expected = k * period
        if abs(d - expected) / expected <= PERIOD_TOLERANCE:
            hits += 1
            ks.append(k)
    score = hits / len(intervals)
    avg_k = (sum(ks) / len(ks)) if ks else 99.0
    return score, avg_k


def _classify_period(intervals: list[int]) -> tuple[float, str] | None:
    """Match a sequence of day-gaps against the canonical period grid.

    Allowing k>1 in the scorer means a single skipped cycle reads as "one
    missed occurrence" of the same period rather than falling out of band
    (the old CV<0.5 check rejected a monthly bill the moment one month was
    missed). When multiple periods pass the conformance bar equally well
    (e.g. 30-day gaps also "fit" biweekly at k=2), the one needing the
    smallest average k wins -- the more natural explanation of the data.
    """
    if not intervals:
        return None
    best: tuple[float, float, float, str] | None = None
    for period, label in PERIOD_GRID:
        score, avg_k = _score_period(intervals, period)
        if score < PERIOD_CONFORMANCE_THRESHOLD:
            continue
        if best is None or score > best[0] + 1e-9 or (
            abs(score - best[0]) <= 1e-9 and avg_k < best[1] - 1e-9
        ):
            best = (score, avg_k, period, label)
    if best is None:
        return None
    return best[2], best[3]


def _classify_kind(amounts: list[float]) -> str:
    """A 'bill' has a near-fixed price (track price changes); a 'habit' is
    naturally variable (weekly groceries -- show the average trend, don't
    alert on every fluctuation)."""
    if len(amounts) < 2:
        return "bill"
    median = statistics.median(amounts)
    if median == 0:
        return "habit"
    mad = statistics.median([abs(a - median) for a in amounts])
    return "bill" if (mad / abs(median)) < BILL_RELATIVE_MAD_THRESHOLD else "habit"


def _recurring_status(today: date, next_due: date, period_days: float) -> str:
    """active / due_soon (due within 7 days) / overdue (>1.5x the period
    late -- "possibly cancelled?")."""
    if (today - next_due).days > 1.5 * period_days:
        return "overdue"
    if (next_due - today).days <= 7:
        return "due_soon"
    return "active"


def _cluster_occurrences(expenses: list[Expense], me: str, other: str) -> list[dict[str, Any]]:
    """Group expenses into description clusters (exact match, then embedding
    similarity) and collapse same-day occurrences within each cluster.

    Shared by recurring-series detection (>=3 occurrences) and
    new-subscription detection (>=2 occurrences, see _detect_new_subscriptions)
    so both operate on identical clustering/occurrence data instead of two
    divergent passes. The >=2 floor here (rather than >=3) exists purely so
    new-subscription detection -- which needs to fire *before* a series has
    accumulated the 3 occurrences _detect_recurring requires -- has data to
    work with; _detect_recurring re-applies its own >=3 gate below.
    """
    if not expenses:
        return []

    desc_map: dict[str, list[Expense]] = defaultdict(list)
    for e in expenses:
        desc_map[e.description].append(e)

    unique_descs = list(desc_map.keys())
    if not unique_descs:
        return []

    try:
        clusters = cluster_descriptions_all(unique_descs, threshold=0.85)
    except Exception:
        # If embedding fails, fall back to exact match only
        clusters = [[i] for i in range(len(unique_descs))]

    result = []
    for cluster_indices in clusters:
        cluster_expenses: list[Expense] = []
        cluster_descs = [unique_descs[i] for i in cluster_indices]
        for desc in cluster_descs:
            cluster_expenses.extend(desc_map[desc])

        if len(cluster_expenses) < 2:
            continue

        cluster_expenses.sort(key=lambda e: (e.date, e.id))

        # Collapse same-day occurrences (sum them) so a same-day duplicate
        # can't inject a 0-day interval and drag the sequence out of shape.
        occ_map: dict[date, list[Expense]] = defaultdict(list)
        for e in cluster_expenses:
            occ_map[e.date].append(e)
        occ_dates = sorted(occ_map.keys())
        if len(occ_dates) < 2:
            continue

        occ_amounts = [round(sum(float(e.amount) for e in occ_map[d]), 2) for d in occ_dates]
        occ_my_amounts = [round(sum(_my_portion(e, me, other) for e in occ_map[d]), 2) for d in occ_dates]

        # Use the most frequent description as the display/canonical name.
        desc_counts: dict[str, int] = defaultdict(int)
        for e in cluster_expenses:
            desc_counts[e.description] += 1
        canonical = max(desc_counts, key=lambda d: desc_counts[d])

        cat_counts: dict[str, int] = defaultdict(int)
        for e in cluster_expenses:
            cat_counts[e.category] += 1
        category = max(cat_counts, key=lambda c: cat_counts[c])

        result.append({
            "canonical": canonical,
            "category": category,
            # The earliest occurrence's description -- unlike `canonical`
            # (most-frequent, which can shift as new expenses arrive), this
            # can never change once a series exists, so it's used as the
            # stable half of the alert-state persistence key (_series_key).
            "first_description": cluster_expenses[0].description,
            "occ_dates": occ_dates,
            "occ_amounts": occ_amounts,
            "occ_my_amounts": occ_my_amounts,
            "cluster_expenses": cluster_expenses,
        })
    return result


def _series_key(category: str, first_description: str) -> str:
    """Stable identity for a recurring series' alert-state row."""
    return f"{category}::{first_description}"


def _detect_recurring(
    expenses: list[Expense],
    me: str,
    other: str,
    today: date | None = None,
    clustered: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], set[int]]:
    """Detect recurring expenses by clustering descriptions and matching
    each cluster's interval sequence against the canonical period grid.

    Returns (series, member_expense_ids). The id set lets the forecast
    exclude these expenses from "variable" category totals, so a recurring
    bill's amount is never counted in both the scheduled and variable
    components.

    `clustered` lets a caller that already ran _cluster_occurrences (the
    main /insights endpoint, which also feeds it to price-step and
    new-subscription detection) pass it straight through instead of
    re-clustering descriptions three times per request; computed internally
    when omitted, e.g. by direct unit-level callers.
    """
    today = today or date.today()
    if not expenses:
        return [], set()
    if clustered is None:
        clustered = _cluster_occurrences(expenses, me, other)

    recurring = []
    member_ids: set[int] = set()

    for c in clustered:
        occ_dates = c["occ_dates"]
        if len(occ_dates) < 3:
            continue
        occ_amounts = c["occ_amounts"]
        occ_my_amounts = c["occ_my_amounts"]

        intervals = [(occ_dates[i + 1] - occ_dates[i]).days for i in range(len(occ_dates) - 1)]
        period_match = _classify_period(intervals)
        if period_match is None:
            continue
        period_days, frequency = period_match

        last3 = occ_amounts[-3:]
        last3_my = occ_my_amounts[-3:]
        last_date = occ_dates[-1]
        next_due = last_date + timedelta(days=round(period_days))

        member_ids.update(e.id for e in c["cluster_expenses"])

        recurring.append({
            "description": c["canonical"],
            "category": c["category"],
            "frequency": frequency,
            "kind": _classify_kind(occ_amounts),
            "avg_amount": round(statistics.mean(occ_amounts), 2),
            "last_amount": occ_amounts[-1],
            "avg_my_amount": round(statistics.mean(occ_my_amounts), 2),
            "last_my_amount": occ_my_amounts[-1],
            "median_amount": round(statistics.median(last3), 2),
            "median_my_amount": round(statistics.median(last3_my), 2),
            "last_date": str(last_date),
            "occurrence_count": len(occ_dates),
            "period_days": round(period_days, 2),
            "next_due": str(next_due),
            "status": _recurring_status(today, next_due, period_days),
        })

    recurring.sort(key=lambda r: (FREQUENCY_ORDER.get(r["frequency"], 99), -r["avg_amount"]))
    return recurring, member_ids


STEP_TOLERANCE = 0.05  # +/-5% counts as "the same price" for run-length/confirmation purposes
STEP_MIN_CHANGE_PCT = 10.0  # minimum |change| to call it a genuine step, not noise
STEP_CONFIRM_COUNT = 3  # occurrences at the new price before it becomes the accepted baseline
STEP_PRIOR_STABILITY_THRESHOLD = 0.10  # relative MAD of the "prior" segment must be below this
NEW_SUBSCRIPTION_MAX_AGE_DAYS = 60


def _trailing_run_length(occ_amounts: list[float]) -> int:
    """Length of the trailing run of occurrences within STEP_TOLERANCE of the
    most recent amount -- i.e. how many occurrences confirm the current
    (possibly newly-stepped) price."""
    if not occ_amounts:
        return 0
    last = occ_amounts[-1]
    n = 1
    for a in reversed(occ_amounts[:-1]):
        if last == 0:
            matches = a == 0
        else:
            matches = abs(a - last) / abs(last) <= STEP_TOLERANCE
        if matches:
            n += 1
        else:
            break
    return n


def _detect_price_step_alerts(
    expenses: list[Expense],
    me: str,
    other: str,
    session: Session,
    today: date | None = None,
    clustered: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Change-point detection on each recurring series' amount sequence:
    compare the median of the last 2-3 occurrences (the "recent" plateau)
    against the median of everything before it (the "prior" plateau).

    Replaces the old last-vs-all-time-mean comparison, which fired
    repeatedly while the mean caught up to a step, went permanently silent
    once it did, and never said what actually changed. Reports the step once
    with the facts that matter (previous price, new price, since when,
    annualized cost delta) and stays visible -- via the alert-state table --
    until STEP_CONFIRM_COUNT occurrences confirm the new price as the
    baseline, or until a person dismisses it.

    See _detect_recurring's `clustered` param for why this accepts a
    pre-computed cluster list instead of always reclustering.
    """
    today = today or date.today()
    if clustered is None:
        clustered = _cluster_occurrences(expenses, me, other)
    alerts = []
    to_commit = False

    for c in clustered:
        occ_dates, occ_amounts, occ_my_amounts = c["occ_dates"], c["occ_amounts"], c["occ_my_amounts"]
        if len(occ_dates) < 4:
            continue

        intervals = [(occ_dates[i + 1] - occ_dates[i]).days for i in range(len(occ_dates) - 1)]
        period_match = _classify_period(intervals)
        if period_match is None:
            continue
        period_days, frequency = period_match

        run_len = _trailing_run_length(occ_amounts)
        if run_len >= STEP_CONFIRM_COUNT or run_len >= len(occ_amounts):
            continue  # new price already confirmed as the baseline, or the whole series is one flat run

        prior_amounts = occ_amounts[:-run_len]
        if len(prior_amounts) < 2:
            continue  # not enough prior history to call this a "stable plateau"

        prior_median = statistics.median(prior_amounts)
        if prior_median == 0:
            continue
        prior_mad = statistics.median([abs(a - prior_median) for a in prior_amounts])
        if (prior_mad / abs(prior_median)) > STEP_PRIOR_STABILITY_THRESHOLD:
            continue  # prior segment wasn't stable enough to call this a clean step

        recent_amounts = occ_amounts[-run_len:]
        recent_my_amounts = occ_my_amounts[-run_len:]
        recent_median = statistics.median(recent_amounts)
        change_pct = round(((recent_median - prior_median) / abs(prior_median)) * 100, 1)
        if abs(change_pct) < STEP_MIN_CHANGE_PCT:
            continue

        prior_my_median = statistics.median(occ_my_amounts[:-run_len])
        recent_my_median = statistics.median(recent_my_amounts)
        since_date = occ_dates[-run_len]
        occurrences_per_year = 365.25 / period_days

        series_key = _series_key(c["category"], c["first_description"])
        if alert_state.is_dismissed_for(session, series_key, "price_step", recent_median):
            continue
        alert_state.record_seen(session, series_key, "price_step", today, baseline_amount=recent_median)
        to_commit = True

        alerts.append({
            "description": c["canonical"],
            "category": c["category"],
            "alert_type": "price_step",
            "previous_avg": prior_median,
            "current_amount": recent_median,
            "my_previous_avg": prior_my_median,
            "my_current_amount": recent_my_median,
            "change_pct": change_pct,
            "direction": "up" if change_pct > 0 else "down",
            "since": str(since_date),
            "frequency": frequency,
            "confirmations": run_len,
            "confirmations_needed": STEP_CONFIRM_COUNT,
            "annualized_delta": round((recent_median - prior_median) * occurrences_per_year, 2),
            "annualized_my_delta": round((recent_my_median - prior_my_median) * occurrences_per_year, 2),
            "series_key": series_key,
        })

    if to_commit:
        session.commit()

    alerts.sort(key=lambda a: -abs(a["change_pct"]))
    return alerts


def _detect_new_subscriptions(
    clustered: list[dict[str, Any]], session: Session, today: date | None = None
) -> list[dict[str, Any]]:
    """Detect the inverse event of a price step: a brand-new recurring
    series. First occurrence <60 days ago, >=2 occurrences already on a
    fixed cadence -- for a couple, "someone signed us up for Disney+" is
    exactly what one partner wants surfaced to the other, well before the
    series would accumulate the 3 occurrences _detect_recurring requires.
    """
    today = today or date.today()
    alerts = []
    to_commit = False

    for c in clustered:
        occ_dates = c["occ_dates"]
        if len(occ_dates) < 2:
            continue
        first_seen = occ_dates[0]
        if (today - first_seen).days >= NEW_SUBSCRIPTION_MAX_AGE_DAYS:
            continue

        intervals = [(occ_dates[i + 1] - occ_dates[i]).days for i in range(len(occ_dates) - 1)]
        period_match = _classify_period(intervals)
        if period_match is None:
            continue
        period_days, frequency = period_match

        series_key = _series_key(c["category"], c["first_description"])
        if alert_state.is_dismissed_for(session, series_key, "new_subscription"):
            continue
        alert_state.record_seen(session, series_key, "new_subscription", today)
        to_commit = True

        alerts.append({
            "description": c["canonical"],
            "category": c["category"],
            "alert_type": "new_subscription",
            "frequency": frequency,
            "first_seen": str(first_seen),
            "occurrence_count": len(occ_dates),
            "amount": c["occ_amounts"][-1],
            "my_amount": c["occ_my_amounts"][-1],
            "series_key": series_key,
        })

    if to_commit:
        session.commit()

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


CATEGORY_TREND_MIN_AMOUNT = 10.0  # skip negligible categories (either side of the comparison)
CATEGORY_TREND_THRESHOLD_PCT = 25.0
CATEGORY_TREND_ATTRIBUTION_FRACTION = 0.5  # >=50% of the excess explained -> suppress as redundant


def _category_trend_alerts(
    expenses: list[Expense],
    me: str,
    other: str,
    anomalies: list[dict[str, Any]],
    price_step_alerts: list[dict[str, Any]],
    today: date | None = None,
) -> list[dict[str, Any]]:
    """Alert when a category's month-to-date spend is off pace vs its usual
    pace through the same day-of-month.

    The old version compared the current, incomplete month's total against
    *full*-month historical averages: on the 12th of the month you're only
    ~40% through it, so nearly every category read "down 60%", and genuine
    overspend didn't read "up" until the final week. Comparing MTD against
    the median MTD-through-the-same-day of the prior 3 months fixes both
    directions of that bug. `three_month_avg` (the field name existing
    frontend already reads) now holds this prorated figure -- the fix only
    matters if what's actually compared/shown changes, not just whether the
    alert fires -- with the old full-month figure kept alongside as
    `three_month_full_avg` for anyone who wants it.

    Attribution: if a category's excess is already explained by an anomaly
    (item 4) or a detected price step (item 2) this month, the alert is
    suppressed here rather than duplicated -- one insight, not three, for
    the same root cause.
    """
    today = today or date.today()
    current_month = _month_key(today)
    current_month_start = today.replace(day=1)
    days_in_current_month = monthrange(today.year, today.month)[1]

    past_months = _complete_month_keys(today, 3)
    if not past_months:
        return []

    earliest_relevant = _month_bounds(past_months[0])[0]
    recent = [e for e in expenses if e.date >= earliest_relevant]

    cat_mtd_my: dict[str, float] = defaultdict(float)
    cat_mtd_shared: dict[str, float] = defaultdict(float)
    cat_full_my: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    cat_full_shared: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    cat_prorated_my: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    cat_prorated_shared: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for e in recent:
        mk = _month_key(e.date)
        my_amt = _my_portion(e, me, other)
        shared_amt = float(e.amount)
        if mk == current_month:
            if e.date <= today:
                cat_mtd_my[e.category] += my_amt
                cat_mtd_shared[e.category] += shared_amt
        elif mk in past_months:
            cat_full_my[e.category][mk] += my_amt
            cat_full_shared[e.category][mk] += shared_amt
            days_in_mk = monthrange(int(mk[:4]), int(mk[5:7]))[1]
            if e.date.day <= min(today.day, days_in_mk):
                cat_prorated_my[e.category][mk] += my_amt
                cat_prorated_shared[e.category][mk] += shared_amt

    categories = set(cat_mtd_my) | set(cat_full_my)

    alerts = []
    for category in categories:
        mtd_amt = cat_mtd_my.get(category, 0.0)
        if mtd_amt == 0:
            continue

        prorated_vals = [cat_prorated_my[category].get(mk, 0.0) for mk in past_months]
        prorated_avg = statistics.median(prorated_vals) if prorated_vals else 0.0
        full_vals_my = [cat_full_my[category].get(mk, 0.0) for mk in past_months]
        full_avg_my = statistics.median(full_vals_my) if full_vals_my else 0.0

        if prorated_avg < CATEGORY_TREND_MIN_AMOUNT and mtd_amt < CATEGORY_TREND_MIN_AMOUNT:
            continue

        if prorated_avg > 0:
            change_pct = round(((mtd_amt - prorated_avg) / prorated_avg) * 100, 1)
        else:
            change_pct = 100.0

        if abs(change_pct) <= CATEGORY_TREND_THRESHOLD_PCT:
            continue

        excess = mtd_amt - prorated_avg

        # ── Attribution pass: suppress if an anomaly or a price step this
        # month already explains most of the excess.
        if excess > 0:
            month_anomalies = [
                a for a in anomalies
                if a["category"] == category and date.fromisoformat(a["date"]) >= current_month_start
            ]
            top_two = sorted((a["my_portion"] for a in month_anomalies), reverse=True)[:2]
            if sum(top_two) >= CATEGORY_TREND_ATTRIBUTION_FRACTION * excess:
                continue

            attributed_by_step = False
            for step in price_step_alerts:
                if step["category"] != category:
                    continue
                step_delta = step["my_current_amount"] - step["my_previous_avg"]
                if step_delta > 0 and step_delta >= CATEGORY_TREND_ATTRIBUTION_FRACTION * excess:
                    attributed_by_step = True
                    break
            if attributed_by_step:
                continue

        shared_mtd = cat_mtd_shared.get(category, 0.0)
        shared_prorated_vals = [cat_prorated_shared[category].get(mk, 0.0) for mk in past_months]
        shared_prorated_avg = statistics.median(shared_prorated_vals) if shared_prorated_vals else 0.0
        shared_full_vals = [cat_full_shared[category].get(mk, 0.0) for mk in past_months]
        shared_full_avg = statistics.median(shared_full_vals) if shared_full_vals else 0.0
        projected_total = round(mtd_amt * (days_in_current_month / today.day), 2) if today.day else mtd_amt
        shared_projected_total = (
            round(shared_mtd * (days_in_current_month / today.day), 2) if today.day else shared_mtd
        )

        alerts.append({
            "category": category,
            "current_month_amount": round(mtd_amt, 2),
            "three_month_avg": round(prorated_avg, 2),
            "three_month_full_avg": round(full_avg_my, 2),
            "projected_total": projected_total,
            "shared_current_month_amount": round(shared_mtd, 2),
            "shared_three_month_avg": round(shared_prorated_avg, 2),
            "shared_three_month_full_avg": round(shared_full_avg, 2),
            "shared_projected_total": shared_projected_total,
            "change_pct": change_pct,
            "direction": "up" if change_pct > 0 else "down",
        })

    alerts.sort(key=lambda a: -abs(a["change_pct"]))
    return alerts


MODIFIED_Z_CONSTANT = 0.6745
MODIFIED_Z_THRESHOLD = 3.5


def _detect_anomalies(expenses: list[Expense], me: str, other: str) -> list[dict[str, Any]]:
    """Flag recent expenses with an unusually high amount for their category,
    using the modified z-score (0.6745 x (x - median) / MAD) with
    leave-one-out baselines.

    Mean/stdev z-scores are the wrong tool here: expense amounts are
    heavy-right-tailed (a mean/stdev pair is dominated by the very outliers
    it's supposed to detect), the candidate itself inflates its own
    baseline when included, and n=5 makes a sample stdev nearly meaningless.
    The median/MAD pair is robust to exactly the skew and small-n issues
    that broke the old approach, and computing each candidate's baseline
    with that candidate excluded (leave-one-out) stops a single large
    purchase from single-handedly widening the spread enough to hide itself.
    "Low" anomalies (an unusually cheap grocery run) are dropped entirely --
    that's not information worth surfacing.

    Statistics prefer the last 12 months so old price levels don't create
    false positives, but fall back to all-time data for categories that are
    sparse in the recent window (fewer than 5 samples).
    """
    today = date.today()
    cutoff = today - timedelta(days=60)
    stats_cutoff = _months_back(today, 12)

    # Build two buckets per category: last-12-months and all-time, each as
    # (expense_id, amount) pairs so a candidate can be excluded by identity
    # (not by value -- two different expenses can share an amount).
    cat_pairs_recent: dict[str, list[tuple[int, float]]] = defaultdict(list)
    cat_pairs_all: dict[str, list[tuple[int, float]]] = defaultdict(list)
    for e in expenses:
        amt = float(e.amount)
        cat_pairs_all[e.category].append((e.id, amt))
        if e.date >= stats_cutoff:
            cat_pairs_recent[e.category].append((e.id, amt))

    def _baseline_pairs(category: str) -> list[tuple[int, float]]:
        """Return recent window if it has enough samples, else fall back to all-time."""
        recent = cat_pairs_recent.get(category, [])
        return recent if len(recent) >= 5 else cat_pairs_all.get(category, [])

    anomalies = []
    for e in expenses:
        if e.date < cutoff:
            continue

        pairs = _baseline_pairs(e.category)
        if len(pairs) < 5:
            continue

        others = [amt for eid, amt in pairs if eid != e.id]
        if len(others) < 4:
            continue

        median = statistics.median(others)
        mad = statistics.median([abs(a - median) for a in others])
        if mad == 0:
            # A perfectly uniform baseline (e.g. ten identical $50 grocery
            # runs) is the exact scenario this candidate would otherwise
            # divide-by-zero on -- and it's precisely where a deviation
            # should read as MOST anomalous, not get silently dropped. A 1%-
            # of-median floor (min 1 cent) keeps the score finite (an
            # unbounded float("inf") would serialize to the non-standard
            # `Infinity` JSON token and break the frontend's JSON.parse)
            # while still producing a very large, clearly-over-threshold
            # score for any real deviation.
            mad = max(abs(median) * 0.01, 0.01)

        z_score = MODIFIED_Z_CONSTANT * (float(e.amount) - median) / mad
        if z_score > MODIFIED_Z_THRESHOLD:
            anomalies.append({
                "id": e.id,
                "description": e.description,
                "category": e.category,
                "amount": float(e.amount),
                "my_portion": round(_my_portion(e, me, other), 2),
                "date": str(e.date),
                "paid_by": e.paid_by,
                "category_median": round(median, 2),
                "category_mad": round(mad, 2),
                "z_score": round(z_score, 1),
                "direction": "high",
            })

    anomalies.sort(key=lambda a: -a["z_score"])
    return anomalies


RECURRING_MONTH_EQUIV_DAYS = 30.44  # average days/month, for a period's monthly-equivalent cost
SEASONALITY_MIN_MONTHS = 13  # need a full year + 1 before same-month-last-year is meaningful
SEASONALITY_BLEND_WEIGHT = 0.3
HIGH_VARIANCE_CV_THRESHOLD = 0.5


def _month_key_offset(month_key: str, months: int) -> str:
    """Shift a YYYY-MM key by +/- months."""
    y, m = int(month_key[:4]), int(month_key[5:7])
    total = y * 12 + (m - 1) + months
    yy, mm = total // 12, total % 12 + 1
    return f"{yy:04d}-{mm:02d}"


def _month_bounds(month_key: str) -> tuple[date, date]:
    y, m = int(month_key[:4]), int(month_key[5:7])
    return date(y, m, 1), date(y, m, monthrange(y, m)[1])


def _complete_month_keys(today: date, n: int) -> list[str]:
    """The n calendar months strictly before the current one, oldest first."""
    current = _month_key(today)
    return [_month_key_offset(current, -i) for i in range(n, 0, -1)]


def _project_due_dates(next_due: date, period_days: float, window_start: date, window_end: date) -> list[date]:
    """Every occurrence of a `next_due`/`period_days` recurring series that
    falls inside [window_start, window_end], whether that means walking
    backward (an overdue series) or forward, and however many times a
    short period (e.g. weekly) repeats within the window."""
    if period_days <= 0:
        return []
    step_days = max(1, round(period_days))
    k_min = math.ceil((window_start - next_due).days / step_days)
    k_max = math.floor((window_end - next_due).days / step_days)
    if k_min > k_max:
        return []
    return [next_due + timedelta(days=k * step_days) for k in range(k_min, k_max + 1)]


def _forecast(
    expenses: list[Expense],
    recurring: list[dict],
    recurring_member_ids: set[int],
    me: str,
    other: str,
    today: date | None = None,
) -> dict[str, Any]:
    """Forecast = scheduled (recurring series due dates) + variable (median
    of recent non-recurring category spend), rebuilt around two ideas the
    old weighted-moving-average couldn't express: a quarterly/annual bill
    only belongs in its due month, and "is this category recurring" is a
    per-series question, not a per-category one (one recurring merchant
    used to make its whole category "recurring").
    """
    today = today or date.today()
    current_month_key = _month_key(today)
    target_month_key = _month_key_offset(current_month_key, 1)

    _empty: dict[str, Any] = {
        "recurring_total": 0, "variable_total": 0, "total_forecast": 0,
        "shared_recurring_total": 0, "shared_variable_total": 0, "shared_total_forecast": 0,
        "last_month_total": 0, "shared_last_month_total": 0, "change_vs_last_month_pct": 0,
        "forecast_month": target_month_key,
        "range": None,
        "by_category": [],
        "scheduled_bills": [],
        "recurring_summary": {
            "active_count": 0, "monthly_equivalent": 0, "annual_equivalent": 0,
            "shared_monthly_equivalent": 0, "shared_annual_equivalent": 0,
        },
        "upcoming_bills": [],
        "on_pace": {
            "month": current_month_key, "mtd_actual": 0, "shared_mtd_actual": 0,
            "remaining_scheduled": 0, "shared_remaining_scheduled": 0,
            "days_left": 0, "estimated_total": 0, "shared_estimated_total": 0,
        },
        "seasonality_applied": False,
    }
    if not expenses:
        return _empty

    earliest_date = min(e.date for e in expenses)
    history_months = (today.year - earliest_date.year) * 12 + (today.month - earliest_date.month) + 1
    has_seasonality_history = history_months >= SEASONALITY_MIN_MONTHS

    # ── Per-category, per-month totals for non-recurring ("variable") spend only —
    # recurring-series expenses are excluded so they're never counted in both
    # the scheduled and variable components.
    var_my: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    var_shared: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for e in expenses:
        if e.id in recurring_member_ids:
            continue
        mk = _month_key(e.date)
        var_my[e.category][mk] += _my_portion(e, me, other)
        var_shared[e.category][mk] += float(e.amount)

    complete_keys = _complete_month_keys(today, 3)

    def _seasonal_estimate(category: str, target_key: str) -> tuple[float, float]:
        """Median of the last 3 complete months' variable spend for
        `category`, blended 30% with the same month last year when the
        category is high-variance (Gift in December, Travel in summer)
        and 13+ months of history exist -- median alone treats a once-a-
        year spike as noise to smooth away instead of a pattern."""
        my_vals = [var_my[category].get(mk, 0.0) for mk in complete_keys]
        shared_vals = [var_shared[category].get(mk, 0.0) for mk in complete_keys]
        my_med = statistics.median(my_vals) if my_vals else 0.0
        shared_med = statistics.median(shared_vals) if shared_vals else 0.0

        if not has_seasonality_history:
            return my_med, shared_med

        nonzero = [v for v in shared_vals if v > 0]
        if len(nonzero) < 2:
            cv = 1.0  # sparse/no data reads as high-variance
        else:
            mean_v = statistics.mean(nonzero)
            cv = (statistics.stdev(nonzero) / mean_v) if mean_v > 0 else 0.0
        if cv <= HIGH_VARIANCE_CV_THRESHOLD:
            return my_med, shared_med

        last_year_key = _month_key_offset(target_key, -12)
        last_year_my = var_my[category].get(last_year_key)
        last_year_shared = var_shared[category].get(last_year_key)
        if last_year_my is None and last_year_shared is None:
            return my_med, shared_med
        w = SEASONALITY_BLEND_WEIGHT
        return (1 - w) * my_med + w * (last_year_my or 0.0), (1 - w) * shared_med + w * (last_year_shared or 0.0)

    categories = set(var_my.keys()) | set(var_shared.keys())
    variable_next = {cat: _seasonal_estimate(cat, target_month_key) for cat in categories}
    variable_current = {cat: _seasonal_estimate(cat, current_month_key) for cat in categories}

    variable_total = round(sum(v[0] for v in variable_next.values()), 2)
    shared_variable_total = round(sum(v[1] for v in variable_next.values()), 2)

    # ── Scheduled component: recurring series due dates landing in the target month.
    # Annual/quarterly bills appear only in their actual due month; a series
    # flagged "overdue" (likely cancelled) is not scheduled going forward.
    target_start, target_end = _month_bounds(target_month_key)
    recurring_total = 0.0
    shared_recurring_total = 0.0
    scheduled_bills = []
    for r in recurring:
        if r["status"] == "overdue":
            continue
        next_due = date.fromisoformat(r["next_due"])
        due_dates = _project_due_dates(next_due, r["period_days"], target_start, target_end)
        if not due_dates:
            continue
        recurring_total += len(due_dates) * r["median_my_amount"]
        shared_recurring_total += len(due_dates) * r["median_amount"]
        for d in due_dates:
            scheduled_bills.append({
                "description": r["description"],
                "category": r["category"],
                "due_date": str(d),
                "amount": r["median_amount"],
                "my_amount": r["median_my_amount"],
            })
    scheduled_bills.sort(key=lambda b: b["due_date"])

    total_forecast = round(recurring_total + variable_total, 2)
    shared_total_forecast = round(shared_recurring_total + shared_variable_total, 2)

    # ── Actuals for the most recently completed calendar month (headline comparison)
    last_month_key = complete_keys[-1] if complete_keys else None
    last_month_total = 0.0
    shared_last_month_total = 0.0
    last_month_by_cat_my: dict[str, float] = defaultdict(float)
    last_month_by_cat_shared: dict[str, float] = defaultdict(float)
    mtd_my = 0.0
    mtd_shared = 0.0
    current_start, current_end = _month_bounds(current_month_key)
    for e in expenses:
        mk = _month_key(e.date)
        my_amt = _my_portion(e, me, other)
        if mk == last_month_key:
            last_month_total += my_amt
            shared_last_month_total += float(e.amount)
            last_month_by_cat_my[e.category] += my_amt
            last_month_by_cat_shared[e.category] += float(e.amount)
        if current_start <= e.date <= today:
            mtd_my += my_amt
            mtd_shared += float(e.amount)
    last_month_total = round(last_month_total, 2)
    shared_last_month_total = round(shared_last_month_total, 2)
    change_pct = (
        round(((total_forecast - last_month_total) / last_month_total) * 100, 1)
        if last_month_total > 0 else 0
    )

    # ── by_category: variable rows only (scheduled bills are reported separately,
    # avoiding the old bug where one recurring merchant made its whole category
    # "recurring" and mixed the two forecasting methods together).
    by_category = []
    for cat in categories:
        my_est, shared_est = variable_next[cat]
        cat_last_my = last_month_by_cat_my.get(cat, 0.0)
        cat_last_shared = last_month_by_cat_shared.get(cat, 0.0)
        if not any([my_est, shared_est, cat_last_my, cat_last_shared]):
            continue
        by_category.append({
            "category": cat,
            "forecast": round(my_est, 2),
            "shared_forecast": round(shared_est, 2),
            "last_month": round(cat_last_my, 2),
            "shared_last_month": round(cat_last_shared, 2),
            "type": "variable",
        })
    by_category.sort(key=lambda x: -x["forecast"])

    # ── Range: P25-P75 of recent complete-month totals (my portion), a spread
    # instead of a false-precision point estimate.
    range_months = [mk for mk in _complete_month_keys(today, 6) if mk >= _month_key(earliest_date)]
    monthly_totals: dict[str, float] = defaultdict(float)
    for e in expenses:
        mk = _month_key(e.date)
        if mk in range_months:
            monthly_totals[mk] += _my_portion(e, me, other)
    totals_series = [monthly_totals.get(mk, 0.0) for mk in range_months]
    forecast_range = None
    if len(totals_series) >= 2:
        q1, _, q3 = statistics.quantiles(totals_series, n=4, method="inclusive")
        forecast_range = {"low": round(min(q1, q3), 2), "high": round(max(q1, q3), 2)}

    # ── Recurring summary / upcoming bills (subscription roll-up)
    active_series = [r for r in recurring if r["status"] in ("active", "due_soon")]
    monthly_equiv_my = sum(r["median_my_amount"] * (RECURRING_MONTH_EQUIV_DAYS / r["period_days"]) for r in active_series)
    monthly_equiv_shared = sum(r["median_amount"] * (RECURRING_MONTH_EQUIV_DAYS / r["period_days"]) for r in active_series)
    recurring_summary = {
        "active_count": len(active_series),
        "monthly_equivalent": round(monthly_equiv_my, 2),
        "annual_equivalent": round(monthly_equiv_my * 12, 2),
        "shared_monthly_equivalent": round(monthly_equiv_shared, 2),
        "shared_annual_equivalent": round(monthly_equiv_shared * 12, 2),
    }
    upcoming_bills = sorted(
        [
            {
                "description": r["description"],
                "category": r["category"],
                "next_due": r["next_due"],
                "amount": r["median_amount"],
                "my_amount": r["median_my_amount"],
                "frequency": r["frequency"],
                "status": r["status"],
            }
            for r in active_series
        ],
        key=lambda b: b["next_due"],
    )[:10]

    # ── On pace (current month): MTD actual + remaining scheduled bills +
    # daily variable rate x days left. This is the Landing-page number.
    days_in_month = monthrange(today.year, today.month)[1]
    days_left = days_in_month - today.day
    remaining_my = 0.0
    remaining_shared = 0.0
    for r in recurring:
        if r["status"] == "overdue":
            continue
        next_due = date.fromisoformat(r["next_due"])
        due_dates = [
            d for d in _project_due_dates(next_due, r["period_days"], current_start, current_end)
            if d > today
        ]
        remaining_my += len(due_dates) * r["median_my_amount"]
        remaining_shared += len(due_dates) * r["median_amount"]

    daily_rate_my = sum(v[0] for v in variable_current.values()) / days_in_month
    daily_rate_shared = sum(v[1] for v in variable_current.values()) / days_in_month

    on_pace = {
        "month": current_month_key,
        "mtd_actual": round(mtd_my, 2),
        "shared_mtd_actual": round(mtd_shared, 2),
        "remaining_scheduled": round(remaining_my, 2),
        "shared_remaining_scheduled": round(remaining_shared, 2),
        "days_left": days_left,
        "estimated_total": round(mtd_my + remaining_my + daily_rate_my * days_left, 2),
        "shared_estimated_total": round(mtd_shared + remaining_shared + daily_rate_shared * days_left, 2),
    }

    return {
        "recurring_total": round(recurring_total, 2),
        "variable_total": variable_total,
        "total_forecast": total_forecast,
        "shared_recurring_total": round(shared_recurring_total, 2),
        "shared_variable_total": shared_variable_total,
        "shared_total_forecast": shared_total_forecast,
        "last_month_total": last_month_total,
        "shared_last_month_total": shared_last_month_total,
        "change_vs_last_month_pct": change_pct,
        "forecast_month": target_month_key,
        "range": forecast_range,
        "by_category": by_category,
        "scheduled_bills": scheduled_bills,
        "recurring_summary": recurring_summary,
        "upcoming_bills": upcoming_bills,
        "on_pace": on_pace,
        "seasonality_applied": has_seasonality_history,
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

    The full payload is cached per (user, mode, day) -- see
    services/insights_cache.py -- since re-embedding every unique
    description and recomputing every section from scratch took many
    seconds at a few thousand expenses. The day is part of the cache key
    because several sections (days-until-due, month-to-date figures) are
    only correct as of "today".
    """
    today = date.today()
    mode = get_app_mode(session)
    cache_key = f"{current_user}|{mode}|{today.isoformat()}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    me, other = resolve_names(session, current_user)
    expenses = _fetch_all_expenses(session)

    # A: Recurring payment detection. Clustering is computed once here and
    # threaded through to price-step and new-subscription detection below,
    # which would otherwise each recluster descriptions from scratch --
    # exactly the kind of redundant per-request work bucket 09's caching
    # item was meant to eliminate.
    clustered = _cluster_occurrences(expenses, me, other)
    recurring, recurring_member_ids = _detect_recurring(expenses, me, other, today, clustered=clustered)

    # B: Anomalies computed first -- item 3's attribution pass (below)
    # references these to avoid emitting a trend alert for the same
    # root cause an anomaly card already explains.
    anomalies = _detect_anomalies(expenses, me, other)

    # C: Price-step alerts (change-point detection) + new-subscription
    # alerts. Price steps are computed before category trends for the same
    # attribution reason as anomalies.
    recurring_alerts = _detect_price_step_alerts(expenses, me, other, session, today, clustered=clustered)
    new_subscription_alerts = _detect_new_subscriptions(clustered, session, today)

    # D: Weekend vs weekday spending (dual view: your + shared)
    weekend_weekday = _weekend_vs_weekday(expenses, me, other)

    # E: Category trend alerts (prorated MTD vs same-day-of-month average,
    # attributed against B and C so a single overspend doesn't fire three
    # separate insights).
    category_trends = _category_trend_alerts(expenses, me, other, anomalies, recurring_alerts, today)

    # F: Next month forecast (scheduled recurring bills + variable spend)
    forecast = _forecast(expenses, recurring, recurring_member_ids, me, other, today)

    # G: Top growing categories (user's portion)
    top_growing = _top_growing_categories(expenses, me, other)

    # H: Income insights (only for solo/hybrid modes)
    income_data = None
    if mode in ("personal", "blended"):
        income_data = _income_insights(session, current_user, me, other, expenses)

    result = {
        "recurring_expenses": recurring,
        "recurring_alerts": recurring_alerts,
        "new_subscription_alerts": new_subscription_alerts,
        "weekend_vs_weekday": weekend_weekday,
        "category_trend_alerts": category_trends,
        "anomalies": anomalies,
        "forecast": forecast,
        "top_growing_categories": top_growing,
        "income_insights": income_data,
        "mode": mode,
    }
    _cache_put(cache_key, result)
    return result


class DismissAlertRequest(BaseModel):
    series_key: str
    alert_type: str


VALID_ALERT_TYPES = {"price_step", "new_subscription"}


@router.post("/insights/alerts/dismiss")
def dismiss_alert(
    payload: DismissAlertRequest,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    """Permanently dismiss a price-step or new-subscription alert.

    Dismissal is scoped to the specific event on file (see
    services/alert_state.py) -- if the same series steps to a *different*
    price later, or a genuinely new series reuses an old series_key (it
    won't, but belt-and-suspenders), the dismissal doesn't carry over.
    """
    if payload.alert_type not in VALID_ALERT_TYPES:
        raise HTTPException(status_code=400, detail=f"alert_type must be one of {sorted(VALID_ALERT_TYPES)}")
    alert_state.dismiss(session, payload.series_key, payload.alert_type, current_user, date.today())
    audit_logger.log(
        "DISMISS_ALERT", current_user,
        {"series_key": payload.series_key, "alert_type": payload.alert_type},
    )
    return {"ok": True}
