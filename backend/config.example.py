import os
from dotenv import load_dotenv

load_dotenv()

# Secret key for session signing — loaded from backend/.env (see .env.example)
SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY environment variable is not set. "
        "Add a long random string to backend/.env (see .env.example)."
    )

BACKUP_PATH = os.getenv("BACKUP_PATH")

VALID_MODES = {"personal", "shared", "blended"}

def get_app_mode(session) -> str:
    """Read app_mode from the Settings table. Returns 'shared' as default."""
    from models import Settings
    row = session.get(Settings, 1)
    if row and row.app_mode in VALID_MODES:
        return row.app_mode
    return "shared"
