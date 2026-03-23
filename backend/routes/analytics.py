from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from database import get_session
from models import Expense

router = APIRouter()


@router.get("/analytics")
def get_analytics(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    session: Session = Depends(get_session),
):
    statement = select(Expense)
    if start_date:
        statement = statement.where(Expense.date >= start_date)
    if end_date:
        statement = statement.where(Expense.date <= end_date)

    expenses = session.exec(statement.order_by(Expense.date.asc())).all()

    # Total spend
    total_spend = sum(e.amount for e in expenses)

    # Total shared spend (exclude Personal)
    shared = [e for e in expenses if e.split_method != "Personal"]
    total_shared_spend = sum(e.amount for e in shared)

    # Spend by category
    by_category: dict[str, float] = {}
    for e in expenses:
        by_category[e.category] = by_category.get(e.category, 0) + e.amount
    category_data = [
        {"category": k, "amount": round(v, 2)}
        for k, v in sorted(by_category.items(), key=lambda x: x[1], reverse=True)
    ]

    # Spend over time (grouped by month)
    by_month: dict[str, float] = {}
    for e in expenses:
        key = e.date.strftime("%Y-%m")
        by_month[key] = by_month.get(key, 0) + e.amount
    time_data = [
        {"month": k, "amount": round(v, 2)} for k, v in sorted(by_month.items())
    ]

    # Category distribution with percentages
    distribution = [
        {
            "category": k,
            "amount": round(v, 2),
            "percentage": round(v / total_spend * 100, 1) if total_spend > 0 else 0,
        }
        for k, v in sorted(by_category.items(), key=lambda x: x[1], reverse=True)
    ]

    # Top 5 largest expenses
    top_expenses = sorted(expenses, key=lambda e: e.amount, reverse=True)[:5]

    return {
        "total_spend": round(total_spend, 2),
        "total_shared_spend": round(total_shared_spend, 2),
        "by_category": category_data,
        "over_time": time_data,
        "distribution": distribution,
        "top_expenses": top_expenses,
    }
