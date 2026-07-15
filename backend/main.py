import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlmodel import Session

from auth import get_current_user, COOKIE_SECURE, IS_DEV
from config import BACKUP_PATH, VALID_MODES, get_app_mode
from users import get_display_names, get_user_count, is_primary_user
from database import (
    create_db_and_tables,
    check_db_integrity,
    ensure_user_preference_columns,
    DB_PATH,
    DATA_DIR,
    get_session,
)
from routes import expenses, analytics, export, insights, income
from auth import router as auth_router
from services.audit import audit_logger
from services.backup import BackupManager

logger = logging.getLogger("mosaic")
logging.basicConfig(level=logging.INFO)

# Backup location: use BACKUP_PATH from config if set, otherwise default to DATA_DIR/backups/
BACKUP_DIR = Path(BACKUP_PATH) if BACKUP_PATH else DATA_DIR / "backups"

# CORS_ORIGINS: comma-separated list of allowed origins.
# Defaults to localhost:5173 for dev. Set to empty string when serving behind a
# same-origin reverse proxy (nginx) or when FastAPI serves the frontend directly.
_cors_raw = os.getenv("CORS_ORIGINS", "http://localhost:5173")
CORS_ORIGINS = [o.strip() for o in _cors_raw.split(",") if o.strip()]

# Frontend dist directory — present after `npm run build` (Method 1: git clone).
# Absent in Docker (nginx serves static files instead).
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
FRONTEND_DIST_RESOLVED = FRONTEND_DIST.resolve()

# Retention/cadence for backups. Both are deliberately-chosen, single values —
# previously main.py passed max_backups=1000 (unbounded disk growth) while
# services/backup.py's own default was 10, and nothing enforced which was in
# effect. 30 is roughly a month of daily backups plus headroom for the
# mutation-triggered ones below.
MAX_BACKUPS = int(os.getenv("MAX_BACKUPS", "30"))
# Back up every N mutations (not only once at process startup), so a
# long-running container's backups stay correlated with actual data change.
BACKUP_EVERY_N_MUTATIONS = int(os.getenv("BACKUP_EVERY_N_MUTATIONS", "20"))


def _warn_if_insecure_cookie_config() -> None:
    """Emit a startup warning for the ENV=production + secure-cookie-default
    footgun: the browser silently drops the session cookie over plain HTTP,
    so login appears to succeed and then every request 401s. We can't detect
    TLS termination from inside the process (a reverse proxy may be doing
    it), so this is a heads-up, not a hard failure. Split out from
    `lifespan` so it's directly unit-testable. See README.md
    "Troubleshooting" and review_order/06-backend-security-access.md #3.
    """
    if not IS_DEV and COOKIE_SECURE:
        logger.warning(
            "Insecure cookie configuration detected: ENV=production with secure "
            "session cookies enabled. If you are serving over plain HTTP (e.g. a "
            "local network without TLS), the browser will silently discard the "
            "session cookie and login will appear to succeed then immediately "
            "401. Set COOKIE_SECURE=false in your environment if you are not "
            "using HTTPS. Ignore this warning if you are genuinely behind a "
            "TLS-terminating reverse proxy."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _warn_if_insecure_cookie_config()

    create_db_and_tables()
    ensure_user_preference_columns()

    # A corrupt database must never boot and start serving traffic — and must
    # never get backed up over a good prior backup. Refuse to start instead.
    if not check_db_integrity():
        raise RuntimeError(
            f"Database integrity check FAILED for {DB_PATH}. Refusing to start "
            f"to avoid serving corrupt data or overwriting a good backup with a "
            f"corrupt one. Restore from the most recent backup in {BACKUP_DIR} "
            f"before restarting."
        )

    backup_mgr = BackupManager(
        db_path=DB_PATH,
        audit_log_path=audit_logger.log_path,
        backup_dir=BACKUP_DIR,
        max_backups=MAX_BACKUPS,
        backup_every_n_mutations=BACKUP_EVERY_N_MUTATIONS,
    )
    backup_mgr.create_backup()
    audit_logger.on_mutation = backup_mgr.notify_mutation

    yield

    audit_logger.on_mutation = None


app = FastAPI(title="Mosaic API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(expenses.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(insights.router, prefix="/api")
app.include_router(income.router, prefix="/api")


@app.get("/api/config")
def get_app_config(session: Session = Depends(get_session)):
    """Public endpoint returning display names and app mode."""
    mode = get_app_mode(session)
    a, b = get_display_names(session)
    count = get_user_count(session)
    return {"userA": a, "userB": b, "mode": mode, "user_count": count}


@app.get("/api/settings")
def get_settings(session: Session = Depends(get_session)):
    mode = get_app_mode(session)
    return {"app_mode": mode}


class SettingsUpdate(BaseModel):
    app_mode: str


@app.put("/api/settings")
def update_settings(
    payload: SettingsUpdate,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    from models import Settings
    new_mode = payload.app_mode
    if new_mode not in VALID_MODES:
        raise HTTPException(status_code=422, detail=f"app_mode must be one of: {', '.join(VALID_MODES)}")
    if new_mode in ("shared", "blended") and get_user_count(session) < 2:
        raise HTTPException(status_code=409, detail="A second user must create an account before switching to this mode.")
    # Only the primary (first-created) user may switch to personal mode — the
    # secondary user could otherwise lock themselves (or the primary user, from
    # the secondary's perspective) out of login, and login's error message for
    # that case ("Invalid username or password") reads as a forgotten password,
    # not a mode change. See review_order/06-backend-security-access.md #2.
    if new_mode == "personal" and get_user_count(session) >= 2 and not is_primary_user(session, current_user):
        raise HTTPException(
            status_code=403,
            detail="Only the primary account holder can switch the app to personal mode.",
        )
    old_mode = get_app_mode(session)
    row = session.get(Settings, 1)
    if row:
        row.app_mode = new_mode
    else:
        row = Settings(id=1, app_mode=new_mode)
    session.add(row)
    session.commit()
    # A mode switch changes how every subsequent entry is interpreted (who can
    # log in, which splits are valid) — audit it like any other mutation.
    if old_mode != new_mode:
        audit_logger.log("MODE_CHANGE", current_user, {"old_mode": old_mode, "new_mode": new_mode})
    return {"app_mode": new_mode}


# ── User Preferences (per-user) ──────────────────────────────────────

@app.get("/api/user-preferences")
def get_user_preferences(
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    from models import UserPreference
    from sqlmodel import select
    row = session.exec(select(UserPreference).where(UserPreference.username == current_user)).first()
    if row:
        return {
            "date_format": row.date_format,
            "currency": row.currency,
            "income_mode_enabled": row.income_mode_enabled,
        }
    return {"date_format": "DD/MM/YYYY", "currency": "CAD", "income_mode_enabled": False}


class UserPreferencesUpdate(BaseModel):
    date_format: Optional[str] = None
    currency: Optional[str] = None
    income_mode_enabled: Optional[bool] = None


@app.put("/api/user-preferences")
def update_user_preferences(
    payload: UserPreferencesUpdate,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    from models import UserPreference, VALID_DATE_FORMATS, VALID_CURRENCIES
    from sqlmodel import select
    if payload.date_format is not None and payload.date_format not in VALID_DATE_FORMATS:
        raise HTTPException(
            status_code=422,
            detail=f"date_format must be one of: {', '.join(sorted(VALID_DATE_FORMATS))}",
        )
    if payload.currency is not None and payload.currency not in VALID_CURRENCIES:
        raise HTTPException(
            status_code=422,
            detail=f"currency must be one of: {', '.join(sorted(VALID_CURRENCIES))}",
        )
    row = session.exec(select(UserPreference).where(UserPreference.username == current_user)).first()
    if not row:
        row = UserPreference(username=current_user)
    if payload.date_format is not None:
        row.date_format = payload.date_format
    if payload.currency is not None:
        row.currency = payload.currency
    if payload.income_mode_enabled is not None:
        row.income_mode_enabled = payload.income_mode_enabled
    session.add(row)
    session.commit()
    return {
        "date_format": row.date_format,
        "currency": row.currency,
        "income_mode_enabled": row.income_mode_enabled,
    }


def resolve_spa_path(full_path: str, dist_dir: Path = FRONTEND_DIST, dist_dir_resolved: Path = FRONTEND_DIST_RESOLVED) -> Path | None:
    """Resolve a requested SPA path and confirm it stays inside dist_dir.

    Returns the resolved Path if safe, or None if it escapes dist_dir (e.g. an
    encoded `../` trying to reach backend/.env or mosaic.db) — the caller must
    treat None as a hard 404, never a fallback to index.html. Split out as a
    standalone function so the containment check is unit-testable without
    frontend/dist needing to exist (it's a build artifact, absent in dev/test).
    """
    candidate = (dist_dir / full_path).resolve()
    if not candidate.is_relative_to(dist_dir_resolved):
        return None
    return candidate


# ── Static file serving (Method 1: git clone + npm run build) ────────────────
# Only activates when frontend/dist/ exists. API routes above take priority.
# In Docker, nginx serves the frontend and this block is never reached.
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        candidate = resolve_spa_path(full_path)
        if candidate is None:
            raise HTTPException(status_code=404)
        if candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(FRONTEND_DIST / "index.html"))
