from decimal import Decimal

import sqlalchemy
from pydantic import field_serializer
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

    @field_serializer("amount")
    def serialize_amount(self, value: Decimal) -> float:
        return float(value)


class Expense(ExpenseBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[str] = Field(default=None)


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(ExpenseBase):
    pass
