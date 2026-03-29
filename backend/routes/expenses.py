from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import case, func, or_
from sqlmodel import Session, select

from auth import get_current_user
from config import USER_A, USER_B
from database import get_session
from models import Expense, ExpenseBase, ExpenseCreate, ExpenseUpdate
from services.audit import audit_logger, expense_to_dict

router = APIRouter()

VALID_PAID_BY = {USER_A, USER_B}
VALID_SPLIT_METHODS = {"50/50", f"100% {USER_A}", f"100% {USER_B}", "Personal"}


def _validate_expense(data: ExpenseBase) -> None:
    if data.amount == 0:
        raise HTTPException(
            status_code=422,
            detail="amount cannot be zero",
        )
    if data.amount < 0 and data.category != "Reimbursement":
        raise HTTPException(
            status_code=422,
            detail="negative amounts are only allowed for Reimbursement",
        )
    if data.date > date.today():
        raise HTTPException(
            status_code=422,
            detail="date cannot be in the future",
        )
    if data.paid_by not in VALID_PAID_BY:
        raise HTTPException(
            status_code=422,
            detail=f"paid_by must be one of: {', '.join(VALID_PAID_BY)}",
        )
    if data.split_method not in VALID_SPLIT_METHODS:
        raise HTTPException(
            status_code=422,
            detail=f"split_method must be one of: {', '.join(VALID_SPLIT_METHODS)}",
        )


@router.get("/expenses")
def list_expenses(
    request: Request,
    search: Optional[str] = None,
    paid_by: Optional[str] = None,
    category: Optional[str] = None,
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
        statement = statement.where(
            or_(
                Expense.description.contains(search),
                Expense.category.contains(search),
                Expense.paid_by.contains(search),
            )
        )
    if paid_by:
        statement = statement.where(Expense.paid_by == paid_by)
    if category:
        statement = statement.where(Expense.category == category)
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
    _validate_expense(data)
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

    _validate_expense(data)
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


def _escape_like(s: str) -> str:
    """Escape SQL LIKE wildcard characters."""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


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

    conditions = [Expense.description.ilike(f"%{_escape_like(kw)}%") for kw in keywords]
    matches = session.exec(select(Expense).where(or_(*conditions))).all()

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
    from fastembed import TextEmbedding
    import numpy as np

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

    # Group by category
    by_category: dict[str, list[tuple[str, int]]] = {}
    for desc, cat, cnt in rows:
        by_category.setdefault(cat, []).append((desc, cnt))

    model = TextEmbedding()
    result = []

    for category, items in by_category.items():
        if len(items) < 2:
            continue

        descriptions = [d for d, _ in items]
        counts = {d: c for d, c in items}

        # Embed all descriptions in this category
        embeddings = list(model.embed(descriptions))
        emb_matrix = np.array(embeddings)

        # Compute cosine similarity matrix
        norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1
        normalized = emb_matrix / norms
        sim_matrix = normalized @ normalized.T

        # Greedy clustering
        visited = set()
        groups = []
        for i in range(len(descriptions)):
            if i in visited:
                continue
            cluster = [i]
            visited.add(i)
            for j in range(i + 1, len(descriptions)):
                if j in visited:
                    continue
                if sim_matrix[i][j] >= threshold:
                    cluster.append(j)
                    visited.add(j)
            if len(cluster) >= 2:
                cluster_descs = [descriptions[k] for k in cluster]
                # Most frequent variant as canonical
                canonical = max(cluster_descs, key=lambda d: counts[d])
                variants = [d for d in cluster_descs if d != canonical]
                groups.append({
                    "canonical": canonical,
                    "variants": variants,
                    "total_count": sum(counts[d] for d in cluster_descs),
                })

        if groups:
            result.append({"category": category, "groups": groups})

    return result


@router.post("/merge-descriptions")
def merge_descriptions(
    payload: dict,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    """Merge variant descriptions into a canonical form within a category."""
    merges = payload.get("merges", [])
    total_updated = 0

    for merge in merges:
        target = merge.get("target", "").strip()
        sources = merge.get("sources", [])
        category = merge.get("category", "")

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
        "merges": merges,
        "total_updated": total_updated,
    })
    return {"updated": total_updated}


@router.get("/balance")
def get_balance(
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    """Calculate net balance between User A and User B via SQL aggregation.

    Positive amount = User A owes User B.
    Negative amount = User B owes User A.
    """
    balance_expr = func.coalesce(
        func.sum(
            case(
                # 50/50: A paid -> B owes half (negative), B paid -> A owes half (positive)
                (
                    (Expense.split_method == "50/50") & (Expense.paid_by == USER_A),
                    -Expense.amount / 2,
                ),
                (
                    (Expense.split_method == "50/50") & (Expense.paid_by == USER_B),
                    Expense.amount / 2,
                ),
                # 100% A: B paid A's share -> A owes B
                (
                    (Expense.split_method == f"100% {USER_A}") & (Expense.paid_by == USER_B),
                    Expense.amount,
                ),
                # 100% B: A paid B's share -> B owes A
                (
                    (Expense.split_method == f"100% {USER_B}") & (Expense.paid_by == USER_A),
                    -Expense.amount,
                ),
                else_=Decimal("0"),
            )
        ),
        Decimal("0"),
    )

    result = session.exec(
        select(balance_expr).where(Expense.split_method != "Personal")
    ).one()
    balance = Decimal(str(result))

    if abs(balance) < Decimal("0.01"):
        description = "All settled up!"
    elif balance > 0:
        description = f"{USER_A} owes {USER_B} ${abs(balance):.2f}"
    else:
        description = f"{USER_B} owes {USER_A} ${abs(balance):.2f}"

    return {"amount": float(round(balance, 2)), "description": description}


@router.get("/monthly-summary")
def get_monthly_summary(
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    """Return category spend totals for the current month via SQL aggregation."""
    today = date.today()
    first_of_month = today.replace(day=1)

    rows = session.exec(
        select(Expense.category, func.sum(Expense.amount).label("total"))
        .where(Expense.date >= first_of_month)
        .where(Expense.category != "Payment")
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc())
    ).all()

    return [
        {"category": cat, "amount": float(round(Decimal(str(total)), 2))}
        for cat, total in rows
    ]
