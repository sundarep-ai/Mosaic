import logging
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{6}$")

logger = logging.getLogger("tallyus")


class BackupManager:
    """Creates timestamped backups of the SQLite database and audit log."""

    def __init__(
        self,
        db_path: Path,
        audit_log_path: Path,
        backup_dir: Path,
        max_backups: int = 10,
    ):
        self.db_path = db_path
        self.audit_log_path = audit_log_path
        self.backup_dir = backup_dir
        self.max_backups = max_backups

    def create_backup(self) -> Path:
        """Create a consistent, timestamped backup of the DB and audit log.

        Uses the SQLite online backup API (sqlite3.Connection.backup) which
        produces a correct snapshot even while the app is running with WAL mode.
        """
        timestamp = datetime.now().strftime("%Y-%m-%dT%H%M%S")
        dest = self.backup_dir / timestamp
        dest.mkdir(parents=True, exist_ok=True)

        # Backup database using the SQLite online backup API
        src_conn = sqlite3.connect(str(self.db_path))
        dst_conn = sqlite3.connect(str(dest / "tallyus.db"))
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
            src_conn.close()

        # Copy audit log if it exists
        if self.audit_log_path.exists():
            shutil.copy2(self.audit_log_path, dest / "audit.jsonl")

        self._rotate_backups()
        logger.info("Backup created at %s", dest)
        return dest

    def _rotate_backups(self) -> None:
        """Keep only the most recent max_backups, delete the rest."""
        if not self.backup_dir.exists():
            return
        backups = sorted(
            [d for d in self.backup_dir.iterdir() if d.is_dir() and _TIMESTAMP_RE.match(d.name)],
            reverse=True,
        )
        for old in backups[self.max_backups :]:
            shutil.rmtree(old)
            logger.info("Rotated old backup: %s", old.name)
