"""Persistence layer for recurring-series alert state (price steps, new
subscriptions) -- see models.SeriesAlertState.

Without this, price-step and new-subscription alerts are pure functions of
the current expense list: a dismissed alert reappears on the very next
reload, and there's no way to know how long an alert has been active across
separate /insights requests. This module is the thin read/upsert layer
routes/insights.py calls into.

Not wired into services/audit.py's mutation-listener/cache-invalidation
machinery on the *read* path (record_seen): this is best-effort bookkeeping
computed as a side effect of an otherwise read-only GET, not a
user-initiated mutation, and firing it on every detection would invalidate
the insights cache on every cache-miss recompute for no benefit (the payload
being built in that same request already reflects the fresh state). Explicit
dismissal (dismiss()) *is* a real user mutation and goes through
audit_logger from the route handler, which does invalidate the cache -- a
dismissed alert must disappear from the very next GET.
"""
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlmodel import Session, select

from models import SeriesAlertState

# Relative tolerance for "is this the same price step (or the same baseline)
# as the one already on file" -- kept in sync with routes/insights.py's own
# STEP_TOLERANCE (duplicated rather than imported to avoid a circular import
# between the route module and this service).
STEP_TOLERANCE = 0.05


def _same_baseline(stored: Decimal | float | None, current: float) -> bool:
    if stored is None:
        return False
    stored = float(stored)
    if stored == 0:
        return current == 0
    return abs(stored - current) / abs(stored) <= STEP_TOLERANCE


def get_state(session: Session, series_key: str, alert_type: str) -> SeriesAlertState | None:
    return session.exec(
        select(SeriesAlertState).where(
            SeriesAlertState.series_key == series_key,
            SeriesAlertState.alert_type == alert_type,
        )
    ).first()


def is_dismissed_for(session: Session, series_key: str, alert_type: str, current_amount: float | None = None) -> bool:
    """True if this series/alert_type is dismissed for the given amount.

    A dismissal is scoped to whatever baseline_amount was on file at the time
    it was dismissed -- if the price has since stepped again (or the
    caller doesn't pass a comparable amount at all, e.g. new-subscription
    alerts), the dismissal no longer applies to this new event.
    """
    row = get_state(session, series_key, alert_type)
    if row is None or not row.dismissed:
        return False
    if current_amount is None:
        return True
    return _same_baseline(row.baseline_amount, current_amount)


def record_seen(
    session: Session,
    series_key: str,
    alert_type: str,
    today: date,
    baseline_amount: float | None = None,
) -> SeriesAlertState:
    """Record that this series/alert_type is actively detected today.

    Does NOT commit -- callers batch several of these per request and commit
    once. Creates a new row on first detection. If a stored baseline_amount
    no longer matches the current one (a second price step landed on top of
    a previously-dismissed one), the row resets: a new event must not
    inherit a dismissal that belonged to a different price.
    """
    row = get_state(session, series_key, alert_type)
    if row is None:
        row = SeriesAlertState(
            series_key=series_key,
            alert_type=alert_type,
            first_seen=today,
            last_seen=today,
            dismissed=False,
            baseline_amount=(
                Decimal(str(round(baseline_amount, 2))) if baseline_amount is not None else None
            ),
        )
        session.add(row)
        return row

    is_new_event = baseline_amount is not None and not _same_baseline(row.baseline_amount, baseline_amount)
    if is_new_event:
        row.first_seen = today
        row.dismissed = False
        row.dismissed_by = None
        row.dismissed_at = None
        row.baseline_amount = Decimal(str(round(baseline_amount, 2)))
    row.last_seen = today
    session.add(row)
    return row


def dismiss(session: Session, series_key: str, alert_type: str, user: str, today: date) -> SeriesAlertState:
    """Mark a series/alert_type dismissed. Commits immediately -- this is
    called from its own dedicated endpoint, not batched with detection."""
    row = get_state(session, series_key, alert_type)
    if row is None:
        row = SeriesAlertState(series_key=series_key, alert_type=alert_type, first_seen=today, last_seen=today)
    row.dismissed = True
    row.dismissed_by = user
    row.dismissed_at = datetime.now(timezone.utc)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
