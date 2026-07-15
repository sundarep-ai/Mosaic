import logging
import os
from pathlib import Path

from sqlalchemy import event, text
from sqlmodel import create_engine, SQLModel, Session

logger = logging.getLogger("mosaic")

# DATA_DIR: where the database, backups, audit logs, and uploads are stored.
# Defaults to the backend/ directory (unchanged local behaviour).
# Set DATA_DIR=/app/data in Docker to persist everything in a mounted volume.
DATA_DIR = Path(os.getenv("DATA_DIR", str(Path(__file__).parent)))
DB_PATH = DATA_DIR / "mosaic.db"
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
    """Run PRAGMA integrity_check on the database. Returns True if healthy.

    A recognizable-but-corrupted SQLite file (bad page checksums, partial
    writes) returns a non-"ok" row from PRAGMA integrity_check. A file that
    isn't SQLite at all (or is corrupted badly enough to lose its header)
    makes sqlite3 raise instead of returning a row — both cases must be
    treated as a failed check, not let the caller crash outright.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA integrity_check")).scalar()
    except Exception:
        logger.exception("Database integrity check raised an error (unreadable/non-SQLite file)")
        return False
    ok = result == "ok"
    if ok:
        logger.info("Database integrity check passed")
    else:
        logger.error("Database integrity check FAILED: %s", result)
    return ok


def ensure_user_preference_columns():
    """Add columns introduced to `userpreference` after its first release.

    SQLModel.metadata.create_all() only creates missing *tables* — it never
    alters an existing table's schema. On a database that already has a
    userpreference table (from when it only had date_format), newly added
    model fields would otherwise be missing from the real SQLite table and
    every query touching them would fail with "no such column".
    """
    with engine.connect() as conn:
        existing = {
            row[1] for row in conn.execute(text("PRAGMA table_info(userpreference)")).fetchall()
        }
        if not existing:
            return  # table doesn't exist yet — create_db_and_tables() will create it with all columns
        if "currency" not in existing:
            conn.execute(text("ALTER TABLE userpreference ADD COLUMN currency VARCHAR(10) NOT NULL DEFAULT 'CAD'"))
        if "income_mode_enabled" not in existing:
            conn.execute(text("ALTER TABLE userpreference ADD COLUMN income_mode_enabled BOOLEAN NOT NULL DEFAULT 0"))
        conn.commit()


def get_session():
    with Session(engine) as session:
        yield session
