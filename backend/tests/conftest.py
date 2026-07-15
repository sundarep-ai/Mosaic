"""
Mosaic backend test configuration.

Bootstraps a mock config module and in-memory SQLite database
so tests run without .env files. Users are seeded in the DB.

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

# Test user credentials (will be seeded into User table)
USER_A = "Alice"
USER_B = "Bob"
USER_A_LOGIN = "alice"
USER_B_LOGIN = "bob"
PASSWORD_A = "testpass_a"
PASSWORD_B = "testpass_b"
SECRET_KEY = "test-secret-key-for-unit-tests-only"
SECURITY_QUESTION = "What is your favorite color?"
SECURITY_ANSWER = "blue"

_hash_a = bcrypt.hashpw(PASSWORD_A.encode(), bcrypt.gensalt()).decode()
_hash_b = bcrypt.hashpw(PASSWORD_B.encode(), bcrypt.gensalt()).decode()
_answer_hash = bcrypt.hashpw(SECURITY_ANSWER.encode(), bcrypt.gensalt()).decode()

_config = types.ModuleType("config")
_config.SECRET_KEY = SECRET_KEY
_config.BACKUP_PATH = ""
_config.VALID_MODES = {"personal", "shared", "blended"}

def _get_app_mode(session) -> str:
    """Delegate to the real get_app_mode (config.example.py) rather than
    reimplementing it — a hand-rolled copy here previously defaulted to
    "shared" with no Settings row, while the shipped default is "personal";
    dozens of tests ran under a mode-resolver that wasn't the real one."""
    from models import Settings
    row = session.get(Settings, 1)
    if row and row.app_mode in _config.VALID_MODES:
        return row.app_mode
    return "personal"

_config.get_app_mode = _get_app_mode
sys.modules["config"] = _config

os.environ["SECRET_KEY"] = SECRET_KEY

# ── 2. Now safe to import app modules ───────────────────────────────
from sqlalchemy import text
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine
from fastapi.testclient import TestClient

import database
from main import app
from models import Expense, User
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
    """Ensure tables exist before each test, seed users, clear data after."""
    SQLModel.metadata.create_all(_test_engine)

    # Seed test users into the User table
    with Session(_test_engine) as s:
        # Clear existing users first (in case previous test left some)
        s.execute(text("DELETE FROM user"))
        s.add(User(
            username=USER_A_LOGIN,
            display_name=USER_A,
            password_hash=_hash_a,
            security_question=SECURITY_QUESTION,
            security_answer_hash=_answer_hash,
        ))
        s.add(User(
            username=USER_B_LOGIN,
            display_name=USER_B,
            password_hash=_hash_b,
            security_question=SECURITY_QUESTION,
            security_answer_hash=_answer_hash,
        ))
        # Mirrors what actually happens in production the moment a 2nd user
        # registers (see main.py/auth.py — registering the 2nd account
        # auto-switches app_mode to "shared"). Seeding users directly like
        # this bypasses that endpoint, so without this row every test would
        # start from the *real* no-Settings-row default of "personal" instead
        # — which is a fine scenario for one dedicated test (see
        # test_settings_default_mode) but not a realistic baseline for the
        # rest of a two-user test suite.
        from models import Settings
        s.add(Settings(id=1, app_mode="shared"))
        s.commit()

    yield

    with Session(_test_engine) as s:
        s.execute(text("DELETE FROM expense"))
        s.execute(text("DELETE FROM income"))
        s.execute(text("DELETE FROM settings"))
        s.execute(text("DELETE FROM dismissedmerge"))
        s.execute(text("DELETE FROM userpreference"))
        s.execute(text("DELETE FROM user"))
        s.commit()


@pytest.fixture(autouse=True)
def _reset_password_reset_rate_limiter():
    """auth._reset_attempts is a module-level dict keyed by username and
    real wall-clock time, entirely independent of the DB — _clean_db never
    touches it. Left alone, a test that trips the forgot-password rate
    limiter would leak failed-attempt counts into any later test in the
    same run that happens to touch the same username within the 5-minute
    window, which easily includes an entire fast test session."""
    import auth as auth_mod
    auth_mod._reset_attempts.clear()
    yield
    auth_mod._reset_attempts.clear()


@pytest.fixture(autouse=True)
def _clear_embedding_cache():
    """services/clustering.py caches description -> embedding globally
    (process-wide, keyed only by description text) so it never re-embeds an
    immutable string twice. That's safe across real requests, but
    test_clustering.py swaps in a fake model with hand-built vectors for
    specific description strings (e.g. "Netflix") -- if a real-model
    embedding for that same string is already cached from another test
    (test_insights.py legitimately uses "Netflix" too), the fake model
    would never even be called."""
    import services.clustering as clustering_mod
    clustering_mod._embedding_cache.clear()
    yield
    clustering_mod._embedding_cache.clear()


@pytest.fixture(autouse=True)
def _clear_insights_cache():
    """services/insights_cache.py is a process-wide dict keyed by
    (user, mode, day), entirely independent of the DB -- _clean_db wiping
    the tables doesn't clear it. Left alone, a cached /insights payload from
    one test would leak into the next test for the same user on the same
    day, e.g. test_mode_in_response's second `set_mode` call bypasses the
    audited /api/settings endpoint (it writes the Settings row directly),
    so the mutation-triggered cache-clear hook never fires for it."""
    import services.insights_cache as cache_mod
    cache_mod.clear()
    yield
    cache_mod.clear()


@pytest.fixture(autouse=True)
def audit_log(tmp_path):
    """Redirect audit logging to a temp directory per test."""
    import services.audit as audit_mod
    import routes.expenses as expenses_mod
    import routes.income as income_mod
    import auth as auth_mod
    import main as main_mod

    test_logger = AuditLogger(tmp_path / "audit")
    old_audit = audit_mod.audit_logger
    old_expenses = expenses_mod.audit_logger
    old_income = income_mod.audit_logger
    old_auth = auth_mod.audit_logger
    old_main = main_mod.audit_logger

    audit_mod.audit_logger = test_logger
    expenses_mod.audit_logger = test_logger
    income_mod.audit_logger = test_logger
    auth_mod.audit_logger = test_logger
    main_mod.audit_logger = test_logger

    yield test_logger

    audit_mod.audit_logger = old_audit
    expenses_mod.audit_logger = old_expenses
    income_mod.audit_logger = old_income
    auth_mod.audit_logger = old_auth
    main_mod.audit_logger = old_main


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
