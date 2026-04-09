from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import Session, select

from auth import get_current_user
from config import get_app_mode
from database import get_session
from models import Expense, Income, IncomeCreate, IncomeUpdate

router = APIRouter()

EXCLUDED_CATEGORIES = ("Payment", "Reimbursement")


def _require_income_mode(session: Session) -> None:
    """Raise 403 if the current app mode does not support income tracking."""
    mode = get_app_mode(session)
    if mode == "shared":
        raise HTTPException(
            status_code=403,
            detail="Income tracking is not available in Shared mode. Switch to Personal or Blended.",
        )


def _dec(val) -> Decimal:
    return Decimal(str(val)) if val else Decimal("0")


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.get("/income")
def list_income(
    request: Request,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    _require_income_mode(session)
    stmt = select(Income).where(Income.user_id == current_user)
    if start_date:
        stmt = stmt.where(Income.date >= start_date)
    if end_date:
        stmt = stmt.where(Income.date <= end_date)
    stmt = stmt.order_by(Income.date.desc())
    return session.exec(stmt).all()


@router.post("/income", status_code=201)
def create_income(
    data: IncomeCreate,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    _require_income_mode(session)
    if data.date > date.today():
        raise HTTPException(status_code=422, detail="date cannot be in the future")
    income = Income(**data.model_dump(), user_id=current_user)
    session.add(income)
    session.commit()
    session.refresh(income)
    return income


@router.put("/income/{income_id}")
def update_income(
    income_id: int,
    data: IncomeUpdate,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    _require_income_mode(session)
    income = session.get(Income, income_id)
    if not income:
        raise HTTPException(status_code=404, detail="Income entry not found")
    if income.user_id != current_user:
        raise HTTPException(status_code=403, detail="You can only edit your own income entries")
    if data.date > date.today():
        raise HTTPException(status_code=422, detail="date cannot be in the future")
    for field, value in data.model_dump().items():
        setattr(income, field, value)
    session.add(income)
    session.commit()
    session.refresh(income)
    return income


@router.delete("/income/{income_id}", status_code=204)
def delete_income(
    income_id: int,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    _require_income_mode(session)
    income = session.get(Income, income_id)
    if not income:
        raise HTTPException(status_code=404, detail="Income entry not found")
    if income.user_id != current_user:
        raise HTTPException(status_code=403, detail="You can only delete your own income entries")
    session.delete(income)
    session.commit()


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------

@router.get("/income/monthly-summary")
def get_monthly_income_summary(
    request: Request,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    """Return total income for the current calendar month for the logged-in user."""
    _require_income_mode(session)
    today = date.today()
    month_start = today.replace(day=1)

    rows = session.exec(
        select(Income.source, func.sum(Income.amount).label("amount"))
        .where(Income.user_id == current_user)
        .where(Income.date >= month_start)
        .where(Income.date <= today)
        .group_by(Income.source)
    ).all()

    total = sum(_dec(r.amount) for r in rows)
    by_source = [{"source": r.source, "amount": float(_dec(r.amount))} for r in rows]
    return {"total": float(total), "count": len(rows), "by_source": by_source}


class SankeyRequest(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None


@router.post("/income/sankey")
def get_income_sankey(
    payload: SankeyRequest,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    """
    Return income + expense data shaped for a Sankey chart.

    Body (all optional):
      { "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD" }

    Response:
      {
        "income_total": float,
        "by_source": [{source, amount}],
        "expenses_total": float,
        "by_category": [{category, amount}],
        "savings": float
      }
    """
    _require_income_mode(session)

    start_date = payload.start_date
    end_date = payload.end_date

    # --- Income side ---
    income_stmt = (
        select(Income.source, func.sum(Income.amount).label("amount"))
        .where(Income.user_id == current_user)
        .group_by(Income.source)
    )
    if start_date:
        income_stmt = income_stmt.where(Income.date >= start_date)
    if end_date:
        income_stmt = income_stmt.where(Income.date <= end_date)

    income_rows = session.exec(income_stmt).all()
    by_source = [{"source": r.source, "amount": float(_dec(r.amount))} for r in income_rows]
    income_total = sum(r["amount"] for r in by_source)

    # --- Expense side: current user's share, excluding Payment + Reimbursement ---
    from routes.expenses import _resolve_names, _my_portion_expr
    me, other = _resolve_names(current_user, session)
    portion_expr = _my_portion_expr(me, other)

    expense_stmt = (
        select(Expense.category, func.sum(portion_expr).label("amount"))
        .group_by(Expense.category)
    )
    for cat in EXCLUDED_CATEGORIES:
        expense_stmt = expense_stmt.where(Expense.category != cat)
    if start_date:
        expense_stmt = expense_stmt.where(Expense.date >= start_date)
    if end_date:
        expense_stmt = expense_stmt.where(Expense.date <= end_date)

    expense_rows = session.exec(expense_stmt).all()
    # Filter out zero-amount categories and sort descending
    by_category = sorted(
        [{"category": r.category, "amount": float(_dec(r.amount))} for r in expense_rows if _dec(r.amount) > 0],
        key=lambda x: x["amount"],
        reverse=True,
    )
    expenses_total = sum(r["amount"] for r in by_category)

    savings = max(0.0, round(income_total - expenses_total, 2))

    return {
        "income_total": round(income_total, 2),
        "by_source": by_source,
        "expenses_total": round(expenses_total, 2),
        "by_category": by_category,
        "savings": savings,
    }
