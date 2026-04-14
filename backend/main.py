import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlmodel import Session

from auth import get_current_user
from config import BACKUP_PATH, VALID_MODES, get_app_mode
from users import get_display_names, get_user_count
from database import create_db_and_tables, check_db_integrity, ensure_indexes, DB_PATH, DATA_DIR, get_session
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    ensure_indexes()

    # Integrity check
    check_db_integrity()

    # Startup backup
    backup_mgr = BackupManager(
        db_path=DB_PATH,
        audit_log_path=audit_logger.log_path,
        backup_dir=BACKUP_DIR,
        max_backups=1000,
    )
    backup_mgr.create_backup()

    yield


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
    row = session.get(Settings, 1)
    if row:
        row.app_mode = new_mode
    else:
        row = Settings(id=1, app_mode=new_mode)
    session.add(row)
    session.commit()
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
        return {"date_format": row.date_format}
    return {"date_format": "DD/MM/YYYY"}


class UserPreferencesUpdate(BaseModel):
    date_format: str


@app.put("/api/user-preferences")
def update_user_preferences(
    payload: UserPreferencesUpdate,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    from models import UserPreference, VALID_DATE_FORMATS
    from sqlmodel import select
    if payload.date_format not in VALID_DATE_FORMATS:
        raise HTTPException(
            status_code=422,
            detail=f"date_format must be one of: {', '.join(sorted(VALID_DATE_FORMATS))}",
        )
    row = session.exec(select(UserPreference).where(UserPreference.username == current_user)).first()
    if row:
        row.date_format = payload.date_format
    else:
        row = UserPreference(username=current_user, date_format=payload.date_format)
    session.add(row)
    session.commit()
    return {"date_format": row.date_format}


# ── Static file serving (Method 1: git clone + npm run build) ────────────────
# Only activates when frontend/dist/ exists. API routes above take priority.
# In Docker, nginx serves the frontend and this block is never reached.
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_DIST / "index.html"))
