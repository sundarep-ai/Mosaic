import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import USER_A, USER_B, BACKUP_PATH
from database import create_db_and_tables, check_db_integrity, ensure_indexes, DB_PATH
from routes import expenses, analytics, export, insights
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


@app.get("/api/config")
def get_app_config():
    """Public endpoint returning display names only. Login usernames are served via authenticated endpoints."""
    return {
        "userA": USER_A,
        "userB": USER_B,
    }
