"""Tests for database.ensure_user_preference_columns().

SQLModel.metadata.create_all() only creates missing tables — it never alters
an existing table's schema. These tests simulate a database that was created
before `currency` and `income_mode_enabled` existed on UserPreference, and
verify the idempotent ALTER TABLE migration brings it up to date safely.
"""

from unittest.mock import patch

from sqlalchemy import text
from sqlalchemy.pool import StaticPool
from sqlmodel import create_engine

import database


def _make_legacy_engine():
    """An in-memory engine with a userpreference table in its *old* shape
    (id, username, date_format only — no currency/income_mode_enabled)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.connect() as conn:
        conn.execute(text(
            "CREATE TABLE userpreference ("
            "id INTEGER PRIMARY KEY, "
            "username VARCHAR(100) UNIQUE NOT NULL, "
            "date_format VARCHAR(20) NOT NULL DEFAULT 'DD/MM/YYYY'"
            ")"
        ))
        conn.execute(text(
            "INSERT INTO userpreference (username, date_format) VALUES ('alice', 'MM/DD/YYYY')"
        ))
        conn.commit()
    return engine


def test_adds_missing_columns_to_legacy_table():
    engine = _make_legacy_engine()
    with patch.object(database, "engine", engine):
        database.ensure_user_preference_columns()

    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT username, date_format, currency, income_mode_enabled FROM userpreference"
        )).first()
    assert row.username == "alice"
    assert row.date_format == "MM/DD/YYYY"  # existing data untouched
    assert row.currency == "CAD"  # new column gets the documented default
    assert row.income_mode_enabled == 0


def test_idempotent_when_columns_already_exist():
    """Running it twice (e.g. two app restarts) must not raise."""
    engine = _make_legacy_engine()
    with patch.object(database, "engine", engine):
        database.ensure_user_preference_columns()
        database.ensure_user_preference_columns()  # should be a no-op, not an error

    with engine.connect() as conn:
        row = conn.execute(text("SELECT currency FROM userpreference")).first()
    assert row.currency == "CAD"


def test_no_op_when_table_does_not_exist_yet():
    """A brand-new database has no userpreference table until create_all()
    runs — this must not raise before that."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with patch.object(database, "engine", engine):
        database.ensure_user_preference_columns()  # no table — should just return
