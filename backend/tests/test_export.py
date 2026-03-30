"""Tests for XLSX export endpoint."""

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
