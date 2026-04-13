import logging
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field as PydanticField

logger = logging.getLogger(__name__)
from sqlalchemy import case, func, or_
from sqlmodel import Session, select

from auth import get_current_user
from database import get_session
from models import Expense, ExpenseBase, ExpenseCreate, ExpenseUpdate, DismissedMerge
from services.audit import audit_logger, expense_to_dict
from users import resolve_names, get_display_names

from services.clustering import get_embedding_model, cluster_descriptions
from utils import escape_like


router = APIRouter()

VALID_CATEGORIES = {
    "Groceries", "Rent", "Utilities", "Dining", "Transportation",
    "Entertainment", "Healthcare", "Shopping", "Travel", "Payment",
    "Other", "Gas", "Car Insurance", "Car Maintenance", "Home Care",
    "Pet Care", "Pet Insurance", "Vet", "Gift", "Subscription",
    "Parking", "Tenant Insurance", "Reimbursement",
}


def _resolve_names(current_user: str, session: Session) -> tuple:
    """Return (my_display_name, other_display_name) for the logged-in user."""
    return resolve_names(session, current_user)


def _my_portion_expr(me: str, other: str):
    """SQL CASE expression returning the current user's portion of each expense.

    Payment is always 0 — callers also filter it at query level, but guarding
    it here prevents incorrect results if the filter is ever omitted.
    """
    return case(
        (Expense.category == "Payment", 0),
        (
            (Expense.split_method == "Personal") & (Expense.paid_by == me),
            Expense.amount,
        ),
        (Expense.split_method == "50/50", Expense.amount / 2),
        (Expense.split_method == f"100% {me}", Expense.amount),
        (Expense.split_method == f"100% {other}", 0),
        (
            (Expense.split_method == "Personal") & (Expense.paid_by == other),
            0,
        ),
        else_=0,
    )


def _get_valid_sets(session: Session):
    """Return (valid_paid_by, valid_split_methods) based on current app mode."""
    from config import get_app_mode
    mode = get_app_mode(session)
    a, b = get_display_names(session)
    if mode == "personal":
        return {a}, {"Personal"}
    return {a, b}, {"50/50", f"100% {a}", f"100% {b}", "Personal"}


def _validate_expense(data: ExpenseBase, session: Session) -> None:
    valid_paid_by, valid_split_methods = _get_valid_sets(session)
    if data.amount == 0:
        raise HTTPException(status_code=422, detail="amount cannot be zero")
    if data.amount < 0 and data.category != "Reimbursement":
        raise HTTPException(status_code=422, detail="negative amounts are only allowed for Reimbursement")
    if data.date > date.today():
        raise HTTPException(status_code=422, detail="date cannot be in the future")
    if data.category not in VALID_CATEGORIES:
        raise HTTPException(status_code=422, detail="invalid category")
    if data.paid_by not in valid_paid_by:
        raise HTTPException(status_code=422, detail=f"paid_by must be one of: {', '.join(valid_paid_by)}")
    if data.split_method not in valid_split_methods:
        raise HTTPException(status_code=422, detail=f"split_method must be one of: {', '.join(valid_split_methods)}")
    if data.split_method == f"100% {data.paid_by}":
        raise HTTPException(status_code=422, detail="split_method cannot assign 100% to the payer themselves")


@router.get("/expenses")
def list_expenses(
    request: Request,
    search: Optional[str] = None,
    paid_by: Optional[str] = None,
    category: Optional[str] = None,
    filter_type: Optional[str] = None,
    limit: Optional[int] = None,
    sort: Optional[str] = "desc",
    sort_by: Optional[str] = "date",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    statement = select(Expense)

    if search:
        escaped = escape_like(search)
        statement = statement.where(
            or_(
                Expense.description.like(f"%{escaped}%", escape="\\"),
                Expense.category.like(f"%{escaped}%", escape="\\"),
                Expense.paid_by.like(f"%{escaped}%", escape="\\"),
            )
        )
    if paid_by:
        statement = statement.where(Expense.paid_by == paid_by)
    if category:
        statement = statement.where(Expense.category == category)
    if filter_type == "personal":
        statement = statement.where(Expense.split_method == "Personal")
    elif filter_type == "shared":
        statement = statement.where(Expense.split_method != "Personal")
    if start_date:
        statement = statement.where(Expense.date >= start_date)
    if end_date:
        statement = statement.where(Expense.date <= end_date)

    order_col = Expense.amount if sort_by == "amount" else Expense.date
    if sort == "desc":
        statement = statement.order_by(order_col.desc(), Expense.id.desc())
    else:
        statement = statement.order_by(order_col.asc(), Expense.id.asc())

    if limit:
        statement = statement.limit(limit)

    return session.exec(statement).all()


@router.get("/expenses/{expense_id}")
def get_expense(
    expense_id: int,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    expense = session.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


@router.post("/expenses", status_code=201)
def create_expense(
    data: ExpenseCreate,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    _validate_expense(data, session)
    expense = Expense.model_validate(data)
    expense.user_id = current_user
    session.add(expense)
    session.commit()
    session.refresh(expense)
    audit_logger.log("CREATE", current_user, expense_to_dict(expense))
    return expense


@router.put("/expenses/{expense_id}")
def update_expense(
    expense_id: int,
    data: ExpenseUpdate,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    expense = session.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    # Allow edit if legacy row (no owner) or if current user owns it
    if expense.user_id is not None and expense.user_id != current_user:
        raise HTTPException(status_code=403, detail="Not authorized to modify this expense")

    _validate_expense(data, session)
    before = expense_to_dict(expense)
    update_data = data.model_dump()
    for key, value in update_data.items():
        setattr(expense, key, value)
    expense.user_id = current_user

    session.add(expense)
    session.commit()
    session.refresh(expense)
    audit_logger.log("UPDATE", current_user, expense_to_dict(expense), before=before)
    return expense


@router.delete("/expenses/{expense_id}")
def delete_expense(
    expense_id: int,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    expense = session.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    if expense.user_id is not None and expense.user_id != current_user:
        raise HTTPException(status_code=403, detail="Not authorized to delete this expense")
    deleted_data = expense_to_dict(expense)
    session.delete(expense)
    session.commit()
    audit_logger.log("DELETE", current_user, deleted_data)
    return {"ok": True}


@router.get("/suggest-category")
def suggest_category(
    description: str = "",
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    """Suggest a category based on historical expenses with similar descriptions.

    Uses a frequency-weighted approach: categories that appear more often with
    matching keywords score higher, rewarding consistency over one-off matches.
    """
    keywords = [w for w in description.strip().lower().split() if len(w) >= 3]
    if not keywords:
        return {"category": None}

    conditions = [Expense.description.ilike(f"%{escape_like(kw)}%", escape="\\") for kw in keywords]
    matches = session.exec(
        select(Expense)
        .where(or_(*conditions))
        .order_by(Expense.date.desc())
        .limit(500)
    ).all()

    if not matches:
        return {"category": None}

    # Frequency-weighted scoring: each match contributes (keyword_hits / total_keywords)
    # so categories with many consistent matches outweigh single high-overlap matches.
    category_score: dict[str, float] = {}
    category_freq: dict[str, int] = {}
    for e in matches:
        desc_lower = e.description.lower()
        hits = sum(1 for kw in keywords if kw in desc_lower)
        relevance = hits / len(keywords)
        category_score[e.category] = category_score.get(e.category, 0) + relevance
        category_freq[e.category] = category_freq.get(e.category, 0) + 1

    best = max(category_score, key=lambda k: category_score[k])
    return {"category": best}


@router.get("/unique-descriptions")
def unique_descriptions(
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    """Return all unique (description, category, count) tuples for client-side fuzzy matching."""
    rows = session.exec(
        select(
            Expense.description,
            Expense.category,
            func.count().label("count"),
        )
        .group_by(Expense.description, Expense.category)
        .order_by(func.count().desc())
    ).all()
    return [
        {"description": desc, "category": cat, "count": cnt}
        for desc, cat, cnt in rows
    ]


@router.get("/similar-descriptions")
def similar_descriptions(
    threshold: float = Query(default=0.85, ge=0.5, le=1.0),
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    """Find clusters of similar descriptions within each category using embedding similarity."""
    # Fetch unique (description, category, count)
    rows = session.exec(
        select(
            Expense.description,
            Expense.category,
            func.count().label("count"),
        )
        .group_by(Expense.description, Expense.category)
        .order_by(func.count().desc())
    ).all()

    # Load all dismissed pairs into a set for fast lookup
    dismissed_rows = session.exec(select(DismissedMerge)).all()
    dismissed_set: set[tuple[str, str, str]] = {
        (d.category, d.desc_a, d.desc_b) for d in dismissed_rows
    }

    def is_dismissed(category: str, d1: str, d2: str) -> bool:
        a, b = DismissedMerge.make_pair(d1, d2)
        return (category, a, b) in dismissed_set

    # Group by category
    by_category: dict[str, list[tuple[str, int]]] = {}
    for desc, cat, cnt in rows:
        by_category.setdefault(cat, []).append((desc, cnt))

    result = []

    for category, items in by_category.items():
        if len(items) < 2:
            continue

        descriptions = [d for d, _ in items]
        counts = {d: c for d, c in items}

        try:
            clusters = cluster_descriptions(descriptions, threshold)
        except Exception:
            logger.warning("Embedding model unavailable for category '%s'; skipping similarity clustering", category)
            continue
        groups = []
        for cluster_indices in clusters:
            cluster_descs = [descriptions[k] for k in cluster_indices]
            canonical = max(cluster_descs, key=lambda d: counts[d])
            variants = [d for d in cluster_descs if d != canonical]

            # Filter out variants that have been dismissed against the canonical
            variants = [v for v in variants if not is_dismissed(category, canonical, v)]
            if not variants:
                continue

            groups.append({
                "canonical": canonical,
                "variants": variants,
                "total_count": sum(counts[d] for d in [canonical] + variants),
            })

        if groups:
            result.append({"category": category, "groups": groups})

    return result


class MergeRequest(BaseModel):
    target: str = PydanticField(min_length=1, max_length=500)
    sources: list[str] = PydanticField(min_length=1)
    category: str = PydanticField(min_length=1, max_length=100)


class MergePayload(BaseModel):
    merges: list[MergeRequest]


@router.post("/merge-descriptions")
def merge_descriptions(
    payload: MergePayload,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    """Merge variant descriptions into a canonical form within a category."""
    total_updated = 0

    for merge in payload.merges:
        target = merge.target.strip()
        sources = merge.sources
        category = merge.category

        if not target or not sources or not category:
            continue

        # Update all source descriptions to target within the category
        statement = (
            select(Expense)
            .where(Expense.description.in_(sources))
            .where(Expense.category == category)
        )
        expenses = session.exec(statement).all()
        for expense in expenses:
            expense.description = target
            session.add(expense)
        total_updated += len(expenses)

    session.commit()
    audit_logger.log("MERGE", current_user, {
        "merges": [m.model_dump() for m in payload.merges],
        "total_updated": total_updated,
    })
    return {"updated": total_updated}


class DismissRequest(BaseModel):
    category: str
    canonical: str
    variants: list[str]


class DismissPayload(BaseModel):
    dismissals: list[DismissRequest]


@router.post("/dismiss-merge")
def dismiss_merge(
    payload: DismissPayload,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    """Permanently dismiss merge suggestions so they never appear again."""
    added = 0
    for d in payload.dismissals:
        for variant in d.variants:
            desc_a, desc_b = DismissedMerge.make_pair(d.canonical, variant)
            # Check if already dismissed
            existing = session.exec(
                select(DismissedMerge)
                .where(DismissedMerge.category == d.category)
                .where(DismissedMerge.desc_a == desc_a)
                .where(DismissedMerge.desc_b == desc_b)
            ).first()
            if not existing:
                session.add(DismissedMerge(
                    category=d.category,
                    desc_a=desc_a,
                    desc_b=desc_b,
                    dismissed_by=current_user,
                ))
                added += 1
    session.commit()
    audit_logger.log("DISMISS_MERGE", current_user, {
        "dismissals": [d.model_dump() for d in payload.dismissals],
        "added": added,
    })
    return {"dismissed": added}


@router.get("/dismissed-merges")
def list_dismissed_merges(
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    """List all permanently dismissed merge suggestions."""
    rows = session.exec(
        select(DismissedMerge).order_by(DismissedMerge.category)
    ).all()
    # Group by category for frontend consumption
    by_cat: dict[str, list[dict]] = {}
    for r in rows:
        by_cat.setdefault(r.category, []).append({
            "id": r.id,
            "desc_a": r.desc_a,
            "desc_b": r.desc_b,
        })
    return [{"category": cat, "pairs": pairs} for cat, pairs in by_cat.items()]


class UndismissPayload(BaseModel):
    ids: list[int]


@router.post("/undismiss-merge")
def undismiss_merge(
    payload: UndismissPayload,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    """Undo a dismissed merge suggestion so it appears again."""
    removed = 0
    for dismiss_id in payload.ids:
        row = session.get(DismissedMerge, dismiss_id)
        if row:
            session.delete(row)
            removed += 1
    session.commit()
    audit_logger.log("UNDISMISS_MERGE", current_user, {
        "ids": payload.ids,
        "removed": removed,
    })
    return {"undismissed": removed}


@router.get("/balance")
def get_balance(
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    """Calculate net balance between User A and User B via SQL aggregation.

    Positive amount = User A owes User B.
    Negative amount = User B owes User A.
    """
    from config import get_app_mode
    if get_app_mode(session) == "personal":
        return {"amount": 0, "description": "Personal mode"}

    a, b = get_display_names(session)

    balance_expr = func.coalesce(
        func.sum(
            case(
                # 50/50: A paid -> B owes half (negative), B paid -> A owes half (positive)
                (
                    (Expense.split_method == "50/50") & (Expense.paid_by == a),
                    -Expense.amount / 2,
                ),
                (
                    (Expense.split_method == "50/50") & (Expense.paid_by == b),
                    Expense.amount / 2,
                ),
                # 100% A: B paid A's share -> A owes B
                (
                    (Expense.split_method == f"100% {a}") & (Expense.paid_by == b),
                    Expense.amount,
                ),
                # 100% B: A paid B's share -> B owes A
                (
                    (Expense.split_method == f"100% {b}") & (Expense.paid_by == a),
                    -Expense.amount,
                ),
                else_=0,
            )
        ),
        0,
    )

    result = session.exec(
        select(balance_expr).where(Expense.split_method != "Personal")
    ).one()
    balance = Decimal(str(result))

    if abs(balance) < Decimal("0.01"):
        description = "All settled up!"
    elif balance > 0:
        description = f"{a} owes {b} ${abs(balance):.2f}"
    else:
        description = f"{b} owes {a} ${abs(balance):.2f}"

    return {"amount": float(round(balance, 2)), "description": description}


@router.get("/monthly-summary")
def get_monthly_summary(
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    """Return the current user's portion of spend per category for the current month.

    Uses _my_portion_expr so each user sees their own share rather than
    household totals. Categories where the user's portion is zero are omitted.
    """
    today = date.today()
    first_of_month = today.replace(day=1)
    me, other = _resolve_names(current_user, session)
    portion = _my_portion_expr(me, other)

    rows = session.exec(
        select(Expense.category, func.sum(portion).label("total"))
        .where(Expense.date >= first_of_month)
        .where(Expense.category != "Payment")
        .where(Expense.category != "Reimbursement")
        .group_by(Expense.category)
        .order_by(func.sum(portion).desc())
    ).all()

    return [
        {"category": cat, "amount": float(round(Decimal(str(total)), 2))}
        for cat, total in rows
        if total and float(total) > 0
    ]


@router.get("/personal-summary")
def get_personal_summary(
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    """Return total personal spend this month for the current user."""
    me, _ = _resolve_names(current_user, session)
    display_name = me
    today = date.today()
    first_of_month = today.replace(day=1)

    result = session.exec(
        select(func.coalesce(func.sum(Expense.amount), 0))
        .where(Expense.split_method == "Personal")
        .where(Expense.paid_by == display_name)
        .where(Expense.date >= first_of_month)
        .where(Expense.category != "Payment")
        .where(Expense.category != "Reimbursement")
    ).one()

    return {"amount": float(round(Decimal(str(result)), 2))}


@router.get("/my-expense-summary")
def get_my_expense_summary(
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    """Return the current user's total expense and total shared spend for the current month.

    Includes Reimbursements (negative amounts reduce the net total).
    Excludes Payment category.
    """
    from config import get_app_mode

    today = date.today()
    first_of_month = today.replace(day=1)
    me, other = _resolve_names(current_user, session)

    base_filters = (
        select(func.coalesce(func.sum(_my_portion_expr(me, other)), 0))
        .where(Expense.date >= first_of_month)
        .where(Expense.category != "Payment")
    )

    mode = get_app_mode(session)
    if mode == "personal":
        # In personal mode all expenses are Personal paid by me, so my_total = total
        my_total = Decimal(str(session.exec(base_filters).one()))
        return {
            "my_total": float(round(my_total, 2)),
            "total_shared_spend": 0.0,
        }

    my_total = Decimal(str(session.exec(base_filters).one()))

    shared_result = session.exec(
        select(func.coalesce(func.sum(Expense.amount), 0))
        .where(Expense.date >= first_of_month)
        .where(Expense.category != "Payment")
        .where(Expense.split_method != "Personal")
    ).one()
    total_shared = Decimal(str(shared_result))

    return {
        "my_total": float(round(my_total, 2)),
        "total_shared_spend": float(round(total_shared, 2)),
    }
