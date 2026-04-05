"""Tests for XLSX export endpoint."""

from datetime import date, timedelta
from io import BytesIO

import openpyxl

from conftest import make_expense


def test_export_returns_xlsx(auth_client_a):
    auth_client_a.post("/api/expenses", json=make_expense())
    resp = auth_client_a.get("/api/export")
    assert resp.status_code == 200
    assert "spreadsheetml" in resp.headers["content-type"]
    assert "attachment" in resp.headers["content-disposition"]


def test_export_headers(auth_client_a):
    auth_client_a.post("/api/expenses", json=make_expense())
    resp = auth_client_a.get("/api/export")
    wb = openpyxl.load_workbook(BytesIO(resp.content))
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    assert headers == ["ID", "Date", "Description", "Amount", "Category", "Paid By", "Split Method"]


def test_export_contains_data(auth_client_a):
    auth_client_a.post("/api/expenses", json=make_expense(
        description="Walmart run", amount=55.50,
    ))
    resp = auth_client_a.get("/api/export")
    wb = openpyxl.load_workbook(BytesIO(resp.content))
    ws = wb.active
    assert ws.max_row == 2  # header + 1 data row
    assert ws.cell(2, 3).value == "Walmart run"
    assert ws.cell(2, 4).value == 55.5


def test_export_with_category_filter(auth_client_a):
    auth_client_a.post("/api/expenses", json=make_expense(category="Groceries"))
    auth_client_a.post("/api/expenses", json=make_expense(category="Dining"))
    resp = auth_client_a.get("/api/export?category=Groceries")
    wb = openpyxl.load_workbook(BytesIO(resp.content))
    ws = wb.active
    assert ws.max_row == 2  # header + 1 filtered row


# ── Date Filtering (SG-11) ───────────────────────────────────────────


def test_export_with_date_filter(auth_client_a):
    """Export should support start_date and end_date query params."""
    today = date.today()
    yesterday = today - timedelta(days=1)
    auth_client_a.post("/api/expenses", json=make_expense(date=str(today), description="Today"))
    auth_client_a.post("/api/expenses", json=make_expense(date=str(yesterday), description="Yesterday"))
    resp = auth_client_a.get(f"/api/export?start_date={today}&end_date={today}")
    assert resp.status_code == 200
    wb = openpyxl.load_workbook(BytesIO(resp.content))
    ws = wb.active
    assert ws.max_row == 2  # header + 1 row (today only)
    assert ws.cell(2, 3).value == "Today"


def test_export_with_combined_filters(auth_client_a):
    """Export with both category and date filters combined."""
    today = date.today()
    yesterday = today - timedelta(days=1)
    auth_client_a.post("/api/expenses", json=make_expense(date=str(today), category="Groceries"))
    auth_client_a.post("/api/expenses", json=make_expense(date=str(today), category="Dining"))
    auth_client_a.post("/api/expenses", json=make_expense(date=str(yesterday), category="Groceries"))
    resp = auth_client_a.get(f"/api/export?category=Groceries&start_date={today}&end_date={today}")
    wb = openpyxl.load_workbook(BytesIO(resp.content))
    ws = wb.active
    assert ws.max_row == 2  # header + 1 row (today + Groceries only)
