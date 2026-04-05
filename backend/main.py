import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import Session

from auth import get_current_user
from config import USER_A, USER_B, BACKUP_PATH, VALID_MODES, get_app_mode
from database import create_db_and_tables, check_db_integrity, ensure_indexes, DB_PATH, get_session
from routes import expenses, analytics, export, insights, income
from auth import router as auth_router
from services.audit import audit_logger
from services.backup import BackupManager

logger = logging.getLogger("tallyus")
logging.basicConfig(level=logging.INFO)

# Backup location: use BACKUP_PATH from config if set, otherwise default to backend/data/backups/
BACKUP_DIR = Path(BACKUP_PATH) if BACKUP_PATH else Path(__file__).parent / "data" / "backups"


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


app = FastAPI(title="MosaicTally API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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
    return {"userA": USER_A, "userB": USER_B, "mode": mode}


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
    row = session.get(Settings, 1)
    if row:
        row.app_mode = new_mode
    else:
        row = Settings(id=1, app_mode=new_mode)
    session.add(row)
    session.commit()
    return {"app_mode": new_mode}
