from decimal import Decimal

import sqlalchemy
from sqlalchemy import Index, CheckConstraint
from pydantic import field_serializer, field_validator
from sqlmodel import SQLModel, Field, Column
from datetime import date
from typing import Optional


class ExpenseBase(SQLModel):
    date: date
    description: str
    amount: Decimal = Field(sa_column=Column(sqlalchemy.Numeric(10, 2)))
    category: str
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
    app_mode: str = Field(default="duo")  # "solo" | "duo" | "hybrid"
