from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlmodel import Session, select

from config import USER_A, USER_B
from database import get_session
from models import Expense, ExpenseBase, ExpenseCreate, ExpenseUpdate

router = APIRouter()

VALID_PAID_BY = {USER_A, USER_B}
VALID_SPLIT_METHODS = {"50/50", f"100% {USER_A}", f"100% {USER_B}", "Personal"}


def _validate_expense(data: ExpenseBase) -> None:
    if data.amount <= 0:
        raise HTTPException(
            status_code=422,
            detail="amount must be greater than 0",
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
    search: Optional[str] = None,
    paid_by: Optional[str] = None,
    category: Optional[str] = None,
    limit: Optional[int] = None,
    sort: Optional[str] = "desc",
    session: Session = Depends(get_session),
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

    if sort == "desc":
        statement = statement.order_by(Expense.date.desc(), Expense.id.desc())
    else:
        statement = statement.order_by(Expense.date.asc(), Expense.id.asc())

    if limit:
        statement = statement.limit(limit)

    return session.exec(statement).all()


@router.get("/expenses/{expense_id}")
def get_expense(expense_id: int, session: Session = Depends(get_session)):
    expense = session.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


@router.post("/expenses", status_code=201)
def create_expense(data: ExpenseCreate, session: Session = Depends(get_session)):
    _validate_expense(data)
    expense = Expense.model_validate(data)
    session.add(expense)
    session.commit()
    session.refresh(expense)
    return expense


@router.put("/expenses/{expense_id}")
def update_expense(
    expense_id: int, data: ExpenseUpdate, session: Session = Depends(get_session)
):
    expense = session.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    _validate_expense(data)
    update_data = data.model_dump()
    for key, value in update_data.items():
        setattr(expense, key, value)

    session.add(expense)
    session.commit()
    session.refresh(expense)
    return expense


@router.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int, session: Session = Depends(get_session)):
    expense = session.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    session.delete(expense)
    session.commit()
    return {"ok": True}


@router.get("/suggest-category")
def suggest_category(description: str = "", session: Session = Depends(get_session)):
    """Suggest a category based on historical expenses with similar descriptions."""
    keywords = [w for w in description.strip().lower().split() if len(w) >= 3]
    if not keywords:
        return {"category": None}

    conditions = [Expense.description.ilike(f"%{kw}%") for kw in keywords]
    matches = session.exec(select(Expense).where(or_(*conditions))).all()

    if not matches:
        return {"category": None}

    # Score each match by how many keywords it contains, then tally by category
    category_score: dict[str, float] = {}
    for e in matches:
        desc_lower = e.description.lower()
        score = sum(1 for kw in keywords if kw in desc_lower)
        category_score[e.category] = category_score.get(e.category, 0) + score

    best = max(category_score, key=category_score.get)
    return {"category": best}


@router.get("/balance")
def get_balance(session: Session = Depends(get_session)):
    """Calculate net balance between User A and User B.

    Positive amount = User A owes User B.
    Negative amount = User B owes User A.
    """
    expenses = session.exec(select(Expense)).all()

    balance = 0.0
    for e in expenses:
        if e.split_method == "Personal":
            continue
        elif e.split_method == "50/50":
            if e.paid_by == USER_A:
                balance -= e.amount / 2  # B owes A half
            else:
                balance += e.amount / 2  # A owes B half
        elif e.split_method == f"100% {USER_A}":
            # User A is responsible for 100%
            if e.paid_by == USER_B:
                balance += e.amount  # A owes B (B paid A's share)
        elif e.split_method == f"100% {USER_B}":
            # User B is responsible for 100%
            if e.paid_by == USER_A:
                balance -= e.amount  # B owes A (A paid B's share)

    if abs(balance) < 0.01:
        description = "All settled up!"
    elif balance > 0:
        description = f"{USER_A} owes {USER_B} ${abs(balance):.2f}"
    else:
        description = f"{USER_B} owes {USER_A} ${abs(balance):.2f}"

    return {"amount": round(balance, 2), "description": description}


@router.get("/monthly-summary")
def get_monthly_summary(session: Session = Depends(get_session)):
    """Return category spend totals for the current month."""
    today = date.today()
    first_of_month = today.replace(day=1)

    expenses = session.exec(
        select(Expense).where(Expense.date >= first_of_month)
    ).all()

    by_category: dict[str, float] = {}
    for e in expenses:
        if e.category == "Payment":
            continue
        by_category[e.category] = by_category.get(e.category, 0) + e.amount

    return [
        {"category": cat, "amount": round(amt, 2)}
        for cat, amt in sorted(by_category.items(), key=lambda x: x[1], reverse=True)
    ]
