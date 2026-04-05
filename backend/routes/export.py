from datetime import date
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlmodel import Session, select
import openpyxl

from auth import get_current_user
from database import get_session
from models import Expense
from utils import escape_like as _escape_like

router = APIRouter()


@router.get("/export")
def export_expenses(
    request: Request,
    search: Optional[str] = None,
    paid_by: Optional[str] = None,
    category: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    statement = select(Expense)

    if search:
        escaped = _escape_like(search)
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
    if start_date:
        statement = statement.where(Expense.date >= start_date)
    if end_date:
        statement = statement.where(Expense.date <= end_date)

    expenses = session.exec(statement.order_by(Expense.date.desc())).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Expenses"

    headers = ["ID", "Date", "Description", "Amount", "Category", "Paid By", "Split Method"]
    ws.append(headers)

    # Style header row
    for cell in ws[1]:
        cell.font = openpyxl.styles.Font(bold=True)

    for e in expenses:
        ws.append([e.id, str(e.date), e.description, e.amount, e.category, e.paid_by, e.split_method])

    # Auto-fit column widths (approximate)
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.spreadsheet",
        headers={"Content-Disposition": f"attachment; filename=expenses_{date.today().isoformat()}.xlsx"},
    )
