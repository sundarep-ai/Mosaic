from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlmodel import Session, select
import openpyxl

from database import get_session
from models import Expense

router = APIRouter()


@router.get("/export")
def export_expenses(
    search: Optional[str] = None,
    paid_by: Optional[str] = None,
    category: Optional[str] = None,
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
        headers={"Content-Disposition": "attachment; filename=expenses.xlsx"},
    )
