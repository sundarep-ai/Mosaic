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

    all_expenses = session.exec(statement.order_by(Expense.date.asc())).all()

    # Exclude Payment category from analytics
    expenses = [e for e in all_expenses if e.category != "Payment"]

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

    # Spend by payer
    by_payer: dict[str, float] = {}
    payer_count: dict[str, int] = {}
    for e in expenses:
        by_payer[e.paid_by] = by_payer.get(e.paid_by, 0) + e.amount
        payer_count[e.paid_by] = payer_count.get(e.paid_by, 0) + 1
    payer_data = [
        {
            "payer": k,
            "amount": round(v, 2),
            "count": payer_count[k],
        }
        for k, v in sorted(by_payer.items(), key=lambda x: x[1], reverse=True)
    ]

    # Spend by split method
    by_split: dict[str, float] = {}
    split_count: dict[str, int] = {}
    for e in expenses:
        by_split[e.split_method] = by_split.get(e.split_method, 0) + e.amount
        split_count[e.split_method] = split_count.get(e.split_method, 0) + 1
    split_data = [
        {
            "method": k,
            "amount": round(v, 2),
            "count": split_count[k],
        }
        for k, v in sorted(by_split.items(), key=lambda x: x[1], reverse=True)
    ]

    # Top 5 largest expenses
    top_expenses = sorted(expenses, key=lambda e: e.amount, reverse=True)[:5]

    return {
        "total_spend": round(total_spend, 2),
        "total_shared_spend": round(total_shared_spend, 2),
        "by_category": category_data,
        "over_time": time_data,
        "distribution": distribution,
        "by_payer": payer_data,
        "by_split_method": split_data,
        "top_expenses": top_expenses,
    }
