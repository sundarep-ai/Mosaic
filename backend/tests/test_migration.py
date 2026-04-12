"""
Tests for migrate_expenses and migrate_income.

Each test spins up its own in-memory SQLite engine so migrations are fully
isolated from the shared API test database.
"""

from datetime import date
from pathlib import Path
from unittest.mock import patch

import bcrypt
import openpyxl
import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

import migrate_expenses
import migrate_income
from models import Expense, Income, User

# ── Shared test credentials ───────────────────────────────────────────────────

_PASSWORD_HASH = bcrypt.hashpw(b"pass", bcrypt.gensalt()).decode()
_ANSWER_HASH = bcrypt.hashpw(b"answer", bcrypt.gensalt()).decode()
_SECURITY_Q = "What is your pet's name?"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_engine():
    """Fresh in-memory SQLite engine with all tables created."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


def _seed_users(engine, users: list[tuple[str, str]]) -> None:
    """Seed (username, display_name) pairs into the given engine."""
    with Session(engine) as s:
        for username, display_name in users:
            s.add(User(
                username=username,
                display_name=display_name,
                password_hash=_PASSWORD_HASH,
                security_question=_SECURITY_Q,
                security_answer_hash=_ANSWER_HASH,
            ))
        s.commit()


def _write_expenses_xlsx(path: Path, rows: list[dict]) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Date", "Description", "Amount", "Category", "Paid By", "Split Method"])
    for r in rows:
        ws.append([
            r["date"], r["description"], r["amount"],
            r["category"], r["paid_by"], r["split_method"],
        ])
    wb.save(path)


def _write_income_xlsx(path: Path, rows: list[dict]) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Date", "Amount", "Source", "Display Name", "Notes"])
    for r in rows:
        ws.append([
            r["date"], r["amount"], r["source"],
            r["display_name"], r.get("notes"),
        ])
    wb.save(path)


# ── migrate_expenses ──────────────────────────────────────────────────────────

class TestMigrateExpenses:

    def _run(self, engine, xlsx_path: Path):
        """Patch the module-level engine and run migrate()."""
        with (
            patch.object(migrate_expenses, "engine", engine),
            patch.object(migrate_expenses, "create_db_and_tables", lambda: None),
        ):
            migrate_expenses.migrate(str(xlsx_path))

    def test_happy_path(self, tmp_path):
        engine = _make_engine()
        _seed_users(engine, [("alice", "Alice"), ("bob", "Bob")])

        xlsx = tmp_path / "expenses.xlsx"
        _write_expenses_xlsx(xlsx, [
            {"date": "2026-01-10", "description": "Groceries", "amount": 80.00,
             "category": "Groceries", "paid_by": "Alice", "split_method": "50/50"},
            {"date": "2026-01-15", "description": "Rent", "amount": 1200.00,
             "category": "Rent", "paid_by": "Bob", "split_method": "50/50"},
        ])

        self._run(engine, xlsx)

        with Session(engine) as s:
            expenses = s.exec(select(Expense)).all()
        assert len(expenses) == 2
        assert expenses[0].paid_by == "Alice"
        assert expenses[0].amount == 80.00
        assert expenses[1].paid_by == "Bob"
        assert expenses[1].amount == 1200.00

    def test_date_formats(self, tmp_path):
        """All supported date format variants are parsed correctly."""
        engine = _make_engine()
        _seed_users(engine, [("alice", "Alice")])

        xlsx = tmp_path / "expenses.xlsx"
        _write_expenses_xlsx(xlsx, [
            {"date": "2026-01-10", "description": "ISO",
             "amount": 10, "category": "Groceries", "paid_by": "Alice", "split_method": "Personal"},
            {"date": "01/20/2026", "description": "US",
             "amount": 20, "category": "Groceries", "paid_by": "Alice", "split_method": "Personal"},
            {"date": "25/01/2026", "description": "EU",
             "amount": 30, "category": "Groceries", "paid_by": "Alice", "split_method": "Personal"},
        ])

        self._run(engine, xlsx)

        with Session(engine) as s:
            expenses = s.exec(select(Expense).order_by(Expense.amount)).all()
        assert len(expenses) == 3
        assert expenses[0].date == date(2026, 1, 10)
        assert expenses[1].date == date(2026, 1, 20)
        assert expenses[2].date == date(2026, 1, 25)

    def test_unknown_paid_by_raises(self, tmp_path):
        """Migration aborts if a paid_by value doesn't match any display name."""
        engine = _make_engine()
        _seed_users(engine, [("alice", "Alice")])

        xlsx = tmp_path / "expenses.xlsx"
        _write_expenses_xlsx(xlsx, [
            {"date": "2026-01-10", "description": "Groceries", "amount": 80.00,
             "category": "Groceries", "paid_by": "Charlie", "split_method": "50/50"},
        ])

        with pytest.raises(SystemExit) as exc_info:
            self._run(engine, xlsx)
        assert exc_info.value.code == 1

        with Session(engine) as s:
            assert s.exec(select(Expense)).first() is None

    def test_no_registered_users_raises(self, tmp_path):
        """Migration aborts if no users exist in the database."""
        engine = _make_engine()  # no users seeded

        xlsx = tmp_path / "expenses.xlsx"
        _write_expenses_xlsx(xlsx, [
            {"date": "2026-01-10", "description": "Groceries", "amount": 80.00,
             "category": "Groceries", "paid_by": "Alice", "split_method": "50/50"},
        ])

        with pytest.raises(SystemExit) as exc_info:
            self._run(engine, xlsx)
        assert exc_info.value.code == 1

    def test_missing_required_column_raises(self, tmp_path):
        """Migration aborts if a required column header is missing."""
        wb = openpyxl.Workbook()
        ws = wb.active
        # Omit "Paid By"
        ws.append(["Date", "Description", "Amount", "Category", "Split Method"])
        ws.append(["2026-01-10", "Groceries", 80, "Groceries", "50/50"])
        xlsx = tmp_path / "expenses.xlsx"
        wb.save(xlsx)

        engine = _make_engine()
        _seed_users(engine, [("alice", "Alice")])

        with pytest.raises(SystemExit) as exc_info:
            self._run(engine, xlsx)
        assert exc_info.value.code == 1

    def test_unparseable_date_skipped(self, tmp_path, capsys):
        """Rows with unparseable dates are skipped; valid rows still import."""
        engine = _make_engine()
        _seed_users(engine, [("alice", "Alice")])

        xlsx = tmp_path / "expenses.xlsx"
        _write_expenses_xlsx(xlsx, [
            {"date": "not-a-date", "description": "Bad", "amount": 50.00,
             "category": "Groceries", "paid_by": "Alice", "split_method": "Personal"},
            {"date": "2026-01-15", "description": "Good", "amount": 90.00,
             "category": "Groceries", "paid_by": "Alice", "split_method": "Personal"},
        ])

        self._run(engine, xlsx)

        with Session(engine) as s:
            expenses = s.exec(select(Expense)).all()
        assert len(expenses) == 1
        assert expenses[0].description == "Good"

        captured = capsys.readouterr()
        assert "WARNING" in captured.out

    def test_existing_data_prompt_abort(self, tmp_path):
        """If the user answers N when prompted about existing data, no rows are added."""
        engine = _make_engine()
        _seed_users(engine, [("alice", "Alice")])

        # Seed one existing expense
        with Session(engine) as s:
            s.add(Expense(date=date(2025, 1, 1), description="Old", amount=10,
                          category="Groceries", paid_by="Alice", split_method="Personal"))
            s.commit()

        xlsx = tmp_path / "expenses.xlsx"
        _write_expenses_xlsx(xlsx, [
            {"date": "2026-01-10", "description": "New", "amount": 80.00,
             "category": "Groceries", "paid_by": "Alice", "split_method": "Personal"},
        ])

        with (
            patch("builtins.input", return_value="N"),
            pytest.raises(SystemExit) as exc_info,
        ):
            self._run(engine, xlsx)
        assert exc_info.value.code == 0

        with Session(engine) as s:
            expenses = s.exec(select(Expense)).all()
        assert len(expenses) == 1  # only the original
        assert expenses[0].description == "Old"

    def test_existing_data_prompt_continue(self, tmp_path):
        """If the user answers Y, new rows are appended to existing data."""
        engine = _make_engine()
        _seed_users(engine, [("alice", "Alice")])

        with Session(engine) as s:
            s.add(Expense(date=date(2025, 1, 1), description="Old", amount=10,
                          category="Groceries", paid_by="Alice", split_method="Personal"))
            s.commit()

        xlsx = tmp_path / "expenses.xlsx"
        _write_expenses_xlsx(xlsx, [
            {"date": "2026-01-10", "description": "New", "amount": 80.00,
             "category": "Groceries", "paid_by": "Alice", "split_method": "Personal"},
        ])

        with patch("builtins.input", return_value="y"):
            self._run(engine, xlsx)

        with Session(engine) as s:
            expenses = s.exec(select(Expense)).all()
        assert len(expenses) == 2


# ── migrate_income ────────────────────────────────────────────────────────────

class TestMigrateIncome:

    def _run(self, engine, xlsx_path: Path):
        """Patch the module-level engine and run migrate()."""
        with (
            patch.object(migrate_income, "engine", engine),
            patch.object(migrate_income, "create_db_and_tables", lambda: None),
        ):
            migrate_income.migrate(str(xlsx_path))

    def test_happy_path(self, tmp_path):
        engine = _make_engine()
        _seed_users(engine, [("alice", "Alice"), ("bob", "Bob")])

        xlsx = tmp_path / "income.xlsx"
        _write_income_xlsx(xlsx, [
            {"date": "2026-01-01", "amount": 3500.00,
             "source": "Salary / Wages", "display_name": "Alice", "notes": "January salary"},
            {"date": "2026-01-05", "amount": 500.00,
             "source": "Freelance / Side Income", "display_name": "Bob", "notes": None},
        ])

        self._run(engine, xlsx)

        with Session(engine) as s:
            incomes = s.exec(select(Income)).all()
        assert len(incomes) == 2
        # Display name "Alice" must be resolved to login username "alice"
        alice_income = next(i for i in incomes if i.amount == 3500.00)
        assert alice_income.user_id == "alice"
        assert alice_income.notes == "January salary"
        bob_income = next(i for i in incomes if i.amount == 500.00)
        assert bob_income.user_id == "bob"

    def test_display_name_resolves_to_username(self, tmp_path):
        """user_id stored in DB must be the login username, not the display name."""
        engine = _make_engine()
        _seed_users(engine, [("praveenr", "Praveen")])

        xlsx = tmp_path / "income.xlsx"
        _write_income_xlsx(xlsx, [
            {"date": "2026-02-01", "amount": 4000.00,
             "source": "Salary / Wages", "display_name": "Praveen"},
        ])

        self._run(engine, xlsx)

        with Session(engine) as s:
            income = s.exec(select(Income)).first()
        assert income.user_id == "praveenr"
        assert income.user_id != "Praveen"

    def test_unknown_display_name_raises(self, tmp_path):
        """Migration aborts if a display name doesn't match any registered user."""
        engine = _make_engine()
        _seed_users(engine, [("alice", "Alice")])

        xlsx = tmp_path / "income.xlsx"
        _write_income_xlsx(xlsx, [
            {"date": "2026-01-01", "amount": 1000.00,
             "source": "Salary / Wages", "display_name": "Charlie"},
        ])

        with pytest.raises(SystemExit) as exc_info:
            self._run(engine, xlsx)
        assert exc_info.value.code == 1

        with Session(engine) as s:
            assert s.exec(select(Income)).first() is None

    def test_no_registered_users_raises(self, tmp_path):
        engine = _make_engine()  # no users seeded

        xlsx = tmp_path / "income.xlsx"
        _write_income_xlsx(xlsx, [
            {"date": "2026-01-01", "amount": 1000.00,
             "source": "Salary / Wages", "display_name": "Alice"},
        ])

        with pytest.raises(SystemExit) as exc_info:
            self._run(engine, xlsx)
        assert exc_info.value.code == 1

    def test_missing_required_column_raises(self, tmp_path):
        """Migration aborts if a required column header is missing."""
        wb = openpyxl.Workbook()
        ws = wb.active
        # Omit "Display Name"
        ws.append(["Date", "Amount", "Source", "Notes"])
        ws.append(["2026-01-01", 1000, "Salary / Wages", None])
        xlsx = tmp_path / "income.xlsx"
        wb.save(xlsx)

        engine = _make_engine()
        _seed_users(engine, [("alice", "Alice")])

        with pytest.raises(SystemExit) as exc_info:
            self._run(engine, xlsx)
        assert exc_info.value.code == 1

    def test_invalid_source_skipped(self, tmp_path, capsys):
        """Rows with unrecognised income sources are skipped; valid rows import."""
        engine = _make_engine()
        _seed_users(engine, [("alice", "Alice")])

        xlsx = tmp_path / "income.xlsx"
        _write_income_xlsx(xlsx, [
            {"date": "2026-01-01", "amount": 500.00,
             "source": "Gambling Winnings", "display_name": "Alice"},
            {"date": "2026-01-02", "amount": 3000.00,
             "source": "Salary / Wages", "display_name": "Alice"},
        ])

        self._run(engine, xlsx)

        with Session(engine) as s:
            incomes = s.exec(select(Income)).all()
        assert len(incomes) == 1
        assert incomes[0].amount == 3000.00

        captured = capsys.readouterr()
        assert "WARNING" in captured.out

    def test_non_positive_amount_skipped(self, tmp_path, capsys):
        """Rows with zero or negative amounts are skipped."""
        engine = _make_engine()
        _seed_users(engine, [("alice", "Alice")])

        xlsx = tmp_path / "income.xlsx"
        _write_income_xlsx(xlsx, [
            {"date": "2026-01-01", "amount": 0,
             "source": "Salary / Wages", "display_name": "Alice"},
            {"date": "2026-01-02", "amount": -100,
             "source": "Salary / Wages", "display_name": "Alice"},
            {"date": "2026-01-03", "amount": 2000,
             "source": "Salary / Wages", "display_name": "Alice"},
        ])

        self._run(engine, xlsx)

        with Session(engine) as s:
            incomes = s.exec(select(Income)).all()
        assert len(incomes) == 1
        assert incomes[0].amount == 2000

    def test_empty_display_name_skipped(self, tmp_path, capsys):
        """Rows with an empty display name cell are skipped."""
        engine = _make_engine()
        _seed_users(engine, [("alice", "Alice")])

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Date", "Amount", "Source", "Display Name", "Notes"])
        ws.append(["2026-01-01", 1000, "Salary / Wages", "", None])  # empty display name
        ws.append(["2026-01-02", 2000, "Salary / Wages", "Alice", None])
        xlsx = tmp_path / "income.xlsx"
        wb.save(xlsx)

        self._run(engine, xlsx)

        with Session(engine) as s:
            incomes = s.exec(select(Income)).all()
        assert len(incomes) == 1
        assert incomes[0].amount == 2000

    def test_unparseable_date_skipped(self, tmp_path, capsys):
        """Rows with unparseable dates are skipped; valid rows still import."""
        engine = _make_engine()
        _seed_users(engine, [("alice", "Alice")])

        xlsx = tmp_path / "income.xlsx"
        _write_income_xlsx(xlsx, [
            {"date": "not-a-date", "amount": 500.00,
             "source": "Salary / Wages", "display_name": "Alice"},
            {"date": "2026-01-15", "amount": 3000.00,
             "source": "Salary / Wages", "display_name": "Alice"},
        ])

        self._run(engine, xlsx)

        with Session(engine) as s:
            incomes = s.exec(select(Income)).all()
        assert len(incomes) == 1
        assert incomes[0].amount == 3000.00

        captured = capsys.readouterr()
        assert "WARNING" in captured.out

    def test_existing_data_prompt_abort(self, tmp_path):
        """If the user answers N when prompted about existing data, no rows are added."""
        engine = _make_engine()
        _seed_users(engine, [("alice", "Alice")])

        with Session(engine) as s:
            s.add(Income(date=date(2025, 1, 1), amount=1000, source="Salary / Wages",
                         notes=None, user_id="alice"))
            s.commit()

        xlsx = tmp_path / "income.xlsx"
        _write_income_xlsx(xlsx, [
            {"date": "2026-01-01", "amount": 2000.00,
             "source": "Salary / Wages", "display_name": "Alice"},
        ])

        with (
            patch("builtins.input", return_value="N"),
            pytest.raises(SystemExit) as exc_info,
        ):
            self._run(engine, xlsx)
        assert exc_info.value.code == 0

        with Session(engine) as s:
            incomes = s.exec(select(Income)).all()
        assert len(incomes) == 1
        assert incomes[0].amount == 1000

    def test_existing_data_prompt_continue(self, tmp_path):
        """If the user answers Y, new rows are appended to existing data."""
        engine = _make_engine()
        _seed_users(engine, [("alice", "Alice")])

        with Session(engine) as s:
            s.add(Income(date=date(2025, 1, 1), amount=1000, source="Salary / Wages",
                         notes=None, user_id="alice"))
            s.commit()

        xlsx = tmp_path / "income.xlsx"
        _write_income_xlsx(xlsx, [
            {"date": "2026-01-01", "amount": 2000.00,
             "source": "Salary / Wages", "display_name": "Alice"},
        ])

        with patch("builtins.input", return_value="y"):
            self._run(engine, xlsx)

        with Session(engine) as s:
            incomes = s.exec(select(Income)).all()
        assert len(incomes) == 2

    def test_old_user_id_column_header_still_works(self, tmp_path):
        """Sheets with a 'User ID' column header (old format) are still accepted."""
        engine = _make_engine()
        _seed_users(engine, [("alice", "Alice")])

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Date", "Amount", "Source", "User ID", "Notes"])
        ws.append(["2026-01-01", 3000, "Salary / Wages", "Alice", None])
        xlsx = tmp_path / "income.xlsx"
        wb.save(xlsx)

        self._run(engine, xlsx)

        with Session(engine) as s:
            income = s.exec(select(Income)).first()
        assert income is not None
        assert income.user_id == "alice"
