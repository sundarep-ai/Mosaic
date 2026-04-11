from decimal import Decimal
from datetime import date, datetime, timezone
from typing import Optional

import sqlalchemy
from sqlalchemy import Index, CheckConstraint
from pydantic import field_serializer, field_validator
from sqlmodel import SQLModel, Field, Column


class User(SQLModel, table=True):
    """Registered user account."""
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=50, unique=True, index=True)
    display_name: str = Field(max_length=100, unique=True, index=True)
    password_hash: str = Field(max_length=200)
    security_question: str = Field(max_length=300)
    security_answer_hash: str = Field(max_length=200)
    stay_signed_in: bool = Field(default=False)
    session_version: int = Field(default=0)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
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
        """Ensure amounts are stored with exactly 2 decimal places."""
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


class UserPreference(SQLModel, table=True):
    """Per-user preferences (e.g. date display format)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=100, unique=True, index=True)
    date_format: str = Field(default="DD/MM/YYYY", max_length=20)


class IncomeCreate(IncomeBase):
    pass


class IncomeUpdate(IncomeBase):
    pass
