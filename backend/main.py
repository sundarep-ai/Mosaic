import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import USER_A, USER_B, USER_A_LOGIN, USER_B_LOGIN
from database import create_db_and_tables, check_db_integrity, DB_PATH
from routes import expenses, analytics, export
from auth import router as auth_router
from services.audit import audit_logger
from services.backup import BackupManager

logger = logging.getLogger("tallyus")
logging.basicConfig(level=logging.INFO)

# Backup location: use BACKUP_PATH from .env if set, otherwise default to backend/data/backups/
_backup_path = os.getenv("BACKUP_PATH")
BACKUP_DIR = Path(_backup_path) if _backup_path else Path(__file__).parent / "data" / "backups"


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()

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


app = FastAPI(title="TallyUs API", lifespan=lifespan)

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


@app.get("/api/config")
def get_app_config():
    """Public endpoint returning app configuration (user display names and login usernames)."""
    return {
        "userA": USER_A,
        "userB": USER_B,
        "userALogin": USER_A_LOGIN,
        "userBLogin": USER_B_LOGIN,
    }
