from decimal import Decimal
from datetime import date, datetime, timezone
from typing import Optional

import sqlalchemy
from sqlalchemy import Index, CheckConstraint
from pydantic import field_serializer, field_validator
from sqlmodel import SQLModel, Field, Column


class User(SQLModel, table=True):
    """Registered user account.

    Constraint: display_name must be treated as immutable after creation.
    Expense.paid_by stores display_name values directly (no FK). Changing a
    display_name would orphan all historical Expense rows for that user with
    no cascade mechanism. There is intentionally no "change display name"
    feature exposed in the app.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=50, unique=True, index=True)
    display_name: str = Field(max_length=100, unique=True, index=True)
    password_hash: str = Field(max_length=200)
    security_question: str = Field(max_length=300)
    security_answer_hash: str = Field(max_length=200)
    stay_signed_in: bool = Field(default=False)
    session_version: int = Field(default=0)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ExpenseBase(SQLModel):
    date: date
    description: str = Field(max_length=500)
    amount: Decimal = Field(sa_column=Column(sqlalchemy.Numeric(10, 2)))
    category: str = Field(max_length=100)
    paid_by: str
    split_method: str

    @field_validator("amount", mode="before")
    @classmethod
    def round_amount(cls, v):
        """Ensure amounts are stored with exactly 2 decimal places.

        Decimal.quantize's default rounding mode is ROUND_HALF_EVEN (banker's
        rounding): a value exactly at the half-cent (e.g. 10.005) rounds to
        the nearest *even* cent (10.00, not 10.01). This only matters for
        inputs landing exactly on a half-cent, which is rare in practice.
        """
        return Decimal(str(v)).quantize(Decimal("0.01"))

    @field_serializer("amount")
    def serialize_amount(self, value: Decimal) -> float:
        return float(value)


class Expense(ExpenseBase, table=True):
    __table_args__ = (
        Index("ix_expense_date", "date"),
        Index("ix_expense_category", "category"),
        Index("ix_expense_paid_by", "paid_by"),
        CheckConstraint("amount != 0", name="ck_expense_amount_nonzero"),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[str] = Field(default=None)


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(ExpenseBase):
    pass


class Settings(SQLModel, table=True):
    id: int = Field(default=1, primary_key=True)
    app_mode: str = Field(default="personal")  # "personal" | "shared" | "blended"


VALID_INCOME_SOURCES = {"Salary / Wages", "Freelance / Side Income", "Other"}


class IncomeBase(SQLModel):
    date: date
    amount: Decimal = Field(sa_column=Column(sqlalchemy.Numeric(10, 2)))
    source: str  # "Salary / Wages" | "Freelance / Side Income" | "Other"
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("amount", mode="before")
    @classmethod
    def round_and_validate_amount(cls, v):
        d = Decimal(str(v)).quantize(Decimal("0.01"))
        if d <= 0:
            raise ValueError("Income amount must be positive")
        return d

    @field_validator("source", mode="before")
    @classmethod
    def validate_source(cls, v):
        if v not in VALID_INCOME_SOURCES:
            raise ValueError(f"source must be one of {sorted(VALID_INCOME_SOURCES)}")
        return v

    @field_serializer("amount")
    def serialize_amount(self, value: Decimal) -> float:
        return float(value)


class Income(IncomeBase, table=True):
    __table_args__ = (
        Index("ix_income_date", "date"),
        CheckConstraint("amount > 0", name="ck_income_amount_positive"),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)


class DismissedMerge(SQLModel, table=True):
    """Permanently dismissed merge suggestions — stored as (category, desc_a, desc_b) pairs."""
    __table_args__ = (
        Index("ix_dismissed_merge_lookup", "category", "desc_a", "desc_b", unique=True),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    category: str = Field(max_length=100)
    desc_a: str = Field(max_length=500)  # alphabetically smaller
    desc_b: str = Field(max_length=500)  # alphabetically larger
    dismissed_by: str = Field(max_length=100)

    @staticmethod
    def make_pair(d1: str, d2: str) -> tuple[str, str]:
        """Return descriptions in canonical alphabetical order."""
        return (d1, d2) if d1 <= d2 else (d2, d1)


VALID_DATE_FORMATS = {"MM/DD/YYYY", "DD/MM/YYYY", "YYYY/MM/DD", "YYYY/DD/MM"}

VALID_CURRENCIES = {"USD", "EUR", "GBP", "CAD", "AUD", "INR", "JPY", "CNY", "CHF", "SGD"}

# Mirrors the CURRENCIES table in frontend/src/UserPreferencesContext.jsx — keep in sync.
CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "CAD": "C$",
    "AUD": "A$",
    "INR": "₹",
    "JPY": "¥",
    "CNY": "¥",
    "CHF": "CHF",
    "SGD": "S$",
}


class UserPreference(SQLModel, table=True):
    """Per-user preferences (date display format, currency, income tracking toggle).

    New columns added to this table after its first release will not appear in
    already-deployed SQLite databases (SQLModel.metadata.create_all() only
    creates missing tables, it never alters existing ones) — see
    database.ensure_user_preference_columns(), which ALTERs them in on startup.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=100, unique=True, index=True)
    date_format: str = Field(default="DD/MM/YYYY", max_length=20)
    currency: str = Field(default="CAD", max_length=10)
    income_mode_enabled: bool = Field(default=False)


class IncomeCreate(IncomeBase):
    pass


class IncomeUpdate(IncomeBase):
    pass


class SeriesAlertState(SQLModel, table=True):
    """Persisted state for a recurring-series alert (price step or new
    subscription), keyed by series identity -- see
    routes/insights.py::_series_key.

    Without this table, dismissals can't survive a page reload (an alert is
    otherwise a pure function of the current expense list, recomputed fresh
    every request) and there's no way to tell "this alert has been visible
    since it first fired" from "this just appeared" across separate
    requests -- which is what the "new since last visit" badge and stable
    recurring identities need. New table -> created by
    SQLModel.metadata.create_all(); every column has a default (CLAUDE.md:
    no migration tooling exists).
    """
    __table_args__ = (
        Index("ix_series_alert_lookup", "series_key", "alert_type", unique=True),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    series_key: str = Field(max_length=600)
    alert_type: str = Field(max_length=30)  # "price_step" | "new_subscription"
    first_seen: date = Field(default_factory=date.today)
    last_seen: date = Field(default_factory=date.today)
    dismissed: bool = Field(default=False)
    dismissed_by: Optional[str] = Field(default=None, max_length=100)
    dismissed_at: Optional[datetime] = Field(default=None)
    baseline_amount: Optional[Decimal] = Field(
        default=None, sa_column=Column(sqlalchemy.Numeric(10, 2))
    )
