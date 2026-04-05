"""
MosaicTally backend test configuration.

Bootstraps a mock config module and in-memory SQLite database
so tests run without config.py or .env files.

Additional test dependencies (beyond requirements.txt):
    pip install pytest httpx
"""

import os
import sys
import types
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path

import bcrypt
import pytest

# ── 1. Bootstrap mock config BEFORE any app imports ─────────────────
_backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_dir))

USER_A = "Alice"
USER_B = "Bob"
USER_A_LOGIN = "alice"
USER_B_LOGIN = "bob"
PASSWORD_A = "testpass_a"
PASSWORD_B = "testpass_b"
SECRET_KEY = "test-secret-key-for-unit-tests-only"

_hash_a = bcrypt.hashpw(PASSWORD_A.encode(), bcrypt.gensalt()).decode()
_hash_b = bcrypt.hashpw(PASSWORD_B.encode(), bcrypt.gensalt()).decode()

_config = types.ModuleType("config")
_config.USER_A = USER_A
_config.USER_B = USER_B
_config.USER_A_LOGIN = USER_A_LOGIN
_config.USER_B_LOGIN = USER_B_LOGIN
_config.USER_A_PASSWORD = _hash_a
_config.USER_B_PASSWORD = _hash_b
_config.SECRET_KEY = SECRET_KEY
_config.BACKUP_PATH = ""
_config.VALID_MODES = {"solo", "duo", "hybrid"}

def _get_app_mode(session=None):
    if session is None:
        return "duo"
    from models import Settings
    row = session.get(Settings, 1)
    if row and row.app_mode in _config.VALID_MODES:
        return row.app_mode
    return "duo"

_config.get_app_mode = _get_app_mode
sys.modules["config"] = _config

os.environ["SECRET_KEY"] = SECRET_KEY
os.environ["USER_A_PASSWORD"] = _hash_a
os.environ["USER_B_PASSWORD"] = _hash_b

# ── 2. Now safe to import app modules ───────────────────────────────
from sqlalchemy import text
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine
from fastapi.testclient import TestClient

import database
from main import app
from models import Expense
from services.audit import AuditLogger

# ── 3. In-memory test database (shared via StaticPool) ──────────────
_test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

database.engine = _test_engine


def _get_test_session():
    with Session(_test_engine) as session:
        yield session


app.dependency_overrides[database.get_session] = _get_test_session


# ── 4. Replace lifespan (skip backups & integrity checks) ───────────
@asynccontextmanager
async def _test_lifespan(app):
    SQLModel.metadata.create_all(_test_engine)
    yield


app.router.lifespan_context = _test_lifespan


# ── 5. Fixtures ─────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _clean_db():
    """Ensure tables exist before each test, clear data after."""
    SQLModel.metadata.create_all(_test_engine)
    yield
    with Session(_test_engine) as s:
        s.execute(text("DELETE FROM expense"))
        s.execute(text("DELETE FROM income"))
        s.execute(text("DELETE FROM settings"))
        s.commit()


@pytest.fixture(autouse=True)
def audit_log(tmp_path):
    """Redirect audit logging to a temp directory per test."""
    import services.audit as audit_mod
    import routes.expenses as expenses_mod

    test_logger = AuditLogger(tmp_path / "audit")
    old_audit = audit_mod.audit_logger
    old_expenses = expenses_mod.audit_logger

    audit_mod.audit_logger = test_logger
    expenses_mod.audit_logger = test_logger

    yield test_logger

    audit_mod.audit_logger = old_audit
    expenses_mod.audit_logger = old_expenses


@pytest.fixture
def client():
    """Unauthenticated test client."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_client_a():
    """Test client authenticated as User A (Alice)."""
    with TestClient(app) as c:
        resp = c.post("/api/auth/login", json={
            "username": USER_A_LOGIN,
            "password": PASSWORD_A,
        })
        assert resp.status_code == 200
        yield c


@pytest.fixture
def auth_client_b():
    """Test client authenticated as User B (Bob)."""
    with TestClient(app) as c:
        resp = c.post("/api/auth/login", json={
            "username": USER_B_LOGIN,
            "password": PASSWORD_B,
        })
        assert resp.status_code == 200
        yield c


@pytest.fixture
def db():
    """Direct database session for seeding test data."""
    with Session(_test_engine) as s:
        yield s


def make_expense(**overrides) -> dict:
    """Build an expense JSON payload with sensible defaults."""
    data = {
        "date": str(date.today()),
        "description": "Test expense",
        "amount": 100.00,
        "category": "Groceries",
        "paid_by": USER_A,
        "split_method": "50/50",
    }
    data.update(overrides)
    return data


def make_income(**overrides) -> dict:
    """Build an income JSON payload with sensible defaults."""
    data = {
        "date": str(date.today()),
        "amount": 1000.00,
        "source": "Salary / Wages",
        "notes": None,
    }
    data.update(overrides)
    return data


def set_mode(db_session, mode: str) -> None:
    """Helper to set app mode in the test database."""
    from models import Settings
    row = db_session.get(Settings, 1)
    if row:
        row.app_mode = mode
    else:
        row = Settings(id=1, app_mode=mode)
    db_session.add(row)
    db_session.commit()
