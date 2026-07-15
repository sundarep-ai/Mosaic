"""_my_portion_expr (SQL, routes/expenses.py) and _my_portion (Python,
routes/insights.py) are two independently written implementations of the
same "what's my share of this expense" semantics, with no test ensuring
they actually agree (bucket 08, item 3 — the highest-protection gap named
in the review: money-shape bugs where the two paths silently diverge).

This exercises every valid (split_method, paid_by) combination across a
range of odd-cent amounts, where float/Decimal rounding differences between
the SQL and Python code paths are most likely to surface.
"""

from decimal import Decimal

from sqlmodel import select

from conftest import USER_A, USER_B, make_expense
from models import Expense
from routes.expenses import _my_portion_expr
from routes.insights import _my_portion

ODD_CENT_AMOUNTS = ["100.01", "33.33", "10.07", "0.03", "99.99", "0.01", "250.55", "1234.56"]

# Every (split_method, paid_by) combination the API actually allows —
# "100% <payer>" is rejected by _validate_expense (can't assign 100% to
# the person who paid), so those two directions are intentionally absent.
SPLIT_DIRECTIONS = [
    ("Personal", "me"),
    ("Personal", "other"),
    ("50/50", "me"),
    ("50/50", "other"),
    ("100% me", "other"),
    ("100% other", "me"),
]


def test_my_portion_expr_and_my_portion_agree_for_odd_cents(auth_client_a, db):
    me, other = USER_A, USER_B

    for amount in ODD_CENT_AMOUNTS:
        for split_template, payer in SPLIT_DIRECTIONS:
            split_method = split_template.replace("me", me).replace("other", other)
            paid_by = me if payer == "me" else other

            resp = auth_client_a.post("/api/expenses", json=make_expense(
                amount=amount, paid_by=paid_by, split_method=split_method,
                category="Groceries",
            ))
            assert resp.status_code == 201, resp.json()
            expense_id = resp.json()["id"]

            expense = db.get(Expense, expense_id)
            python_portion = round(_my_portion(expense, me, other), 2)

            sql_result = db.exec(
                select(_my_portion_expr(me, other)).where(Expense.id == expense_id)
            ).one()
            sql_portion = round(float(sql_result), 2)

            assert sql_portion == python_portion, (
                f"amount={amount} split={split_method!r} paid_by={paid_by!r}: "
                f"SQL portion={sql_portion} vs Python portion={python_portion}"
            )

            db.delete(expense)
            db.commit()
