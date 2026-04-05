import logging
from pathlib import Path

from sqlalchemy import event, text
from sqlmodel import create_engine, SQLModel, Session

logger = logging.getLogger("tallyus")

DB_DIR = Path(__file__).parent
DB_PATH = DB_DIR / "tallyus.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def check_db_integrity() -> bool:
    """Run PRAGMA integrity_check on the database. Returns True if healthy."""
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA integrity_check")).scalar()
        ok = result == "ok"
        if ok:
            logger.info("Database integrity check passed")
        else:
            logger.error("Database integrity check FAILED: %s", result)
        return ok


def ensure_indexes():
    """Create indexes if they don't already exist (safe for existing databases)."""
    with engine.connect() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_expense_date ON expense (date)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_expense_category ON expense (category)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_expense_paid_by ON expense (paid_by)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_income_date ON income (date)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_income_user_id ON income (user_id)"))
        conn.commit()


def get_session():
    with Session(engine) as session:
        yield session
