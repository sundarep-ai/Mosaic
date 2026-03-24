from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlmodel import Session, select

from auth import get_current_user
from database import get_session
from models import Expense

router = APIRouter()


def _dec(val) -> Decimal:
    """Safely convert a SQL result to Decimal."""
    return Decimal(str(val)) if val else Decimal("0")


def _date_filters(statement, start_date, end_date):
    """Apply date range and exclude Payment category."""
    if start_date:
        statement = statement.where(Expense.date >= start_date)
    if end_date:
        statement = statement.where(Expense.date <= end_date)
    return statement.where(Expense.category != "Payment")


@router.get("/analytics")
def get_analytics(
    request: Request,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    # Total spend (excluding Payment)
    total_row = session.exec(
        _date_filters(
            select(
                func.coalesce(func.sum(Expense.amount), 0),
                func.coalesce(
                    func.sum(
                        func.iif(Expense.split_method != "Personal", Expense.amount, 0)
                    ),
                    0,
                ),
            ),
            start_date,
            end_date,
        )
    ).one()
    total_spend = _dec(total_row[0])
    total_shared_spend = _dec(total_row[1])

    # Spend by category
    cat_rows = session.exec(
        _date_filters(
            select(Expense.category, func.sum(Expense.amount).label("total"))
            .group_by(Expense.category)
            .order_by(func.sum(Expense.amount).desc()),
            start_date,
            end_date,
        )
    ).all()
    category_data = [
        {"category": cat, "amount": float(round(_dec(total), 2))}
        for cat, total in cat_rows
    ]
    distribution = [
        {
            "category": cat,
            "amount": float(round(_dec(total), 2)),
            "percentage": float(round(_dec(total) / total_spend * 100, 1)) if total_spend > 0 else 0,
        }
        for cat, total in cat_rows
    ]

    # Spend over time (grouped by month) -- use strftime for SQLite
    month_rows = session.exec(
        _date_filters(
            select(
                func.strftime("%Y-%m", Expense.date).label("month"),
                func.sum(Expense.amount).label("total"),
            )
            .group_by(func.strftime("%Y-%m", Expense.date))
            .order_by(func.strftime("%Y-%m", Expense.date)),
            start_date,
            end_date,
        )
    ).all()
    time_data = [
        {"month": month, "amount": float(round(_dec(total), 2))}
        for month, total in month_rows
    ]

    # Spend by payer
    payer_rows = session.exec(
        _date_filters(
            select(
                Expense.paid_by,
                func.sum(Expense.amount).label("total"),
                func.count(Expense.id).label("cnt"),
            )
            .group_by(Expense.paid_by)
            .order_by(func.sum(Expense.amount).desc()),
            start_date,
            end_date,
        )
    ).all()
    payer_data = [
        {"payer": payer, "amount": float(round(_dec(total), 2)), "count": cnt}
        for payer, total, cnt in payer_rows
    ]

    # Spend by split method
    split_rows = session.exec(
        _date_filters(
            select(
                Expense.split_method,
                func.sum(Expense.amount).label("total"),
                func.count(Expense.id).label("cnt"),
            )
            .group_by(Expense.split_method)
            .order_by(func.sum(Expense.amount).desc()),
            start_date,
            end_date,
        )
    ).all()
    split_data = [
        {"method": method, "amount": float(round(_dec(total), 2)), "count": cnt}
        for method, total, cnt in split_rows
    ]

    # Top 5 largest expenses (need full rows, so limited select is fine)
    top_stmt = _date_filters(
        select(Expense), start_date, end_date
    ).order_by(Expense.amount.desc()).limit(5)
    top_expenses = session.exec(top_stmt).all()

    return {
        "total_spend": float(round(total_spend, 2)),
        "total_shared_spend": float(round(total_shared_spend, 2)),
        "by_category": category_data,
        "over_time": time_data,
        "distribution": distribution,
        "by_payer": payer_data,
        "by_split_method": split_data,
        "top_expenses": top_expenses,
    }
