from sqlmodel import SQLModel, Field
from datetime import date
from typing import Optional


class ExpenseBase(SQLModel):
    date: date
    description: str
    amount: float
    category: str
    paid_by: str
    split_method: str


class Expense(ExpenseBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(ExpenseBase):
    pass
