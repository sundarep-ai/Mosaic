"""
Migrate income entries from an existing .xlsx file into the MosaicTally SQLite database.

Usage:
    python migrate_income_xlsx.py path/to/your/income.xlsx

Expected columns (header matching is case-insensitive and flexible):
    Date, Amount, Source, User ID
    Notes  (optional)

Valid sources: "Salary / Wages", "Freelance / Side Income", "Other"
"""

import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation

import openpyxl
from sqlalchemy import func
from sqlmodel import Session, select

from database import engine, create_db_and_tables
from models import Income, VALID_INCOME_SOURCES


def normalize(header: str) -> str:
    return header.strip().lower().replace(" ", "_").replace("-", "_")


def migrate(filepath: str) -> None:
    create_db_and_tables()

    wb = openpyxl.load_workbook(filepath)
    ws = wb.active

    headers = [normalize(str(cell.value)) for cell in ws[1]]

    # Map header keywords to field names
    col_map: dict[str, int] = {}
    for i, h in enumerate(headers):
        if "date" in h:
            col_map.setdefault("date", i)
        elif "amount" in h:
            col_map.setdefault("amount", i)
        elif "source" in h:
            col_map.setdefault("source", i)
        elif "user" in h or "user_id" in h:
            col_map.setdefault("user_id", i)
        elif "note" in h:
            col_map.setdefault("notes", i)

    required = {"date", "amount", "source", "user_id"}
    missing = required - col_map.keys()
    if missing:
        print(f"ERROR: Could not map columns: {missing}")
        print(f"  Found headers: {headers}")
        sys.exit(1)

    valid_sources = sorted(VALID_INCOME_SOURCES)

    with Session(engine) as session:
        existing_count = session.exec(select(func.count(Income.id))).one()
        if existing_count > 0:
            answer = input(
                f"WARNING: Database already has {existing_count} income entries. "
                "Continue and add new rows? [y/N]: "
            )
            if answer.strip().lower() != "y":
                print("Aborted.")
                sys.exit(0)

        count = 0
        skipped = 0
        for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row or row[col_map["date"]] is None:
                continue

            # --- Date ---
            date_val = row[col_map["date"]]
            if isinstance(date_val, str):
                for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y"):
                    try:
                        date_val = datetime.strptime(date_val, fmt).date()
                        break
                    except ValueError:
                        continue
                else:
                    print(f"WARNING: Row {row_num} — skipping unparseable date: {date_val!r}")
                    skipped += 1
                    continue
            elif isinstance(date_val, datetime):
                date_val = date_val.date()

            # --- Amount ---
            raw_amount = row[col_map["amount"]]
            try:
                amount_val = Decimal(str(raw_amount)).quantize(Decimal("0.01"))
                if amount_val <= 0:
                    raise ValueError("non-positive")
            except (InvalidOperation, ValueError):
                print(f"WARNING: Row {row_num} — skipping invalid amount: {raw_amount!r}")
                skipped += 1
                continue

            # --- Source ---
            source_val = str(row[col_map["source"]]).strip()
            if source_val not in VALID_INCOME_SOURCES:
                print(
                    f"WARNING: Row {row_num} — skipping unknown source: {source_val!r}. "
                    f"Valid values: {valid_sources}"
                )
                skipped += 1
                continue

            # --- User ID ---
            user_id_val = str(row[col_map["user_id"]]).strip().lower()
            if not user_id_val:
                print(f"WARNING: Row {row_num} — skipping row with empty user_id")
                skipped += 1
                continue

            # --- Notes (optional) ---
            notes_val = None
            if "notes" in col_map and row[col_map["notes"]] is not None:
                notes_val = str(row[col_map["notes"]]).strip() or None

            income = Income(
                date=date_val,
                amount=amount_val,
                source=source_val,
                notes=notes_val,
                user_id=user_id_val,
            )
            session.add(income)
            count += 1

        session.commit()
        print(f"Successfully migrated {count} income entries into tallyus.db")
        if skipped:
            print(f"Skipped {skipped} rows due to validation errors (see warnings above).")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python migrate_income_xlsx.py <path_to_xlsx>")
        sys.exit(1)
    migrate(sys.argv[1])
