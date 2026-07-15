import logging
import re
import shutil
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

# Microsecond precision avoids two backups within the same second colliding on
# the same destination folder now that backups can also fire mid-session
# (see notify_mutation), not just once at startup. The looser {6,} lower bound
# keeps recognizing older second-precision backup folders already on disk.
_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{6,}$")

logger = logging.getLogger("mosaic")


class BackupManager:
    """Creates timestamped, verified backups of the SQLite database and audit log."""

    def __init__(
        self,
        db_path: Path,
        audit_log_path: Path,
        backup_dir: Path,
        max_backups: int = 10,
        backup_every_n_mutations: Optional[int] = None,
    ):
        self.db_path = db_path
        self.audit_log_path = audit_log_path
        self.backup_dir = backup_dir
        self.max_backups = max_backups
        # If set, notify_mutation() triggers a backup once this many mutations
        # have been observed since the last one — correlating backups with
        # actual data change instead of only firing once at process startup.
        self.backup_every_n_mutations = backup_every_n_mutations
        self._mutation_count = 0
        self._lock = threading.Lock()

    def create_backup(self) -> Path:
        """Create a consistent, timestamped backup of the DB and audit log.

        Uses the SQLite online backup API (sqlite3.Connection.backup) which
        produces a correct snapshot even while the app is running with WAL mode.
        """
        timestamp = datetime.now().strftime("%Y-%m-%dT%H%M%S%f")
        dest = self.backup_dir / timestamp
        dest.mkdir(parents=True, exist_ok=True)

        # Backup database using the SQLite online backup API
        src_conn = sqlite3.connect(str(self.db_path))
        dst_conn = sqlite3.connect(str(dest / "mosaic.db"))
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
            src_conn.close()

        # Copy audit log if it exists
        if self.audit_log_path.exists():
            shutil.copy2(self.audit_log_path, dest / "audit.jsonl")

        if self.verify_backup(dest):
            logger.info("Backup created and verified at %s", dest)
        else:
            logger.error(
                "Backup at %s failed verification — it may not be restorable. "
                "Keeping it for forensics rather than silently deleting it.",
                dest,
            )

        self._rotate_backups()
        return dest

    def verify_backup(self, dest: Path) -> bool:
        """Open the freshly-created backup copy and confirm it's actually restorable.

        A corrupt backup is worse than no backup at all, since it creates false
        confidence that data is safe. Checks PRAGMA integrity_check on the copy
        itself, plus a row-count sanity comparison against the live source.

        Note: the row-count comparison reads the *current* source after the
        backup already completed, so a mutation landing in that gap could cause
        a spurious mismatch on an otherwise-good backup. Given this app's single
        low-concurrency SQLite instance, that window is negligible — this is a
        best-effort sanity check, not a strict guarantee.
        """
        db_copy = dest / "mosaic.db"
        if not db_copy.exists():
            return False
        try:
            conn = sqlite3.connect(str(db_copy))
        except sqlite3.Error:
            logger.exception("Could not open backup at %s for verification", dest)
            return False
        try:
            # A file corrupted badly enough to lose its SQLite header makes
            # sqlite3 raise here instead of returning an error row — either
            # way, the backup isn't restorable.
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                logger.error("Backup at %s failed integrity_check: %s", dest, integrity)
                return False
            return self._row_counts_match(conn)
        except sqlite3.Error:
            logger.exception("Backup at %s could not be read for integrity check", dest)
            return False
        finally:
            conn.close()

    def _row_counts_match(self, backup_conn: sqlite3.Connection) -> bool:
        src_conn = sqlite3.connect(str(self.db_path))
        try:
            tables = [
                row[0]
                for row in src_conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                ).fetchall()
            ]
            for table in tables:
                src_count = src_conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                dst_count = backup_conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                if src_count != dst_count:
                    logger.error(
                        "Backup row-count mismatch in table %s: source=%d backup=%d",
                        table, src_count, dst_count,
                    )
                    return False
            return True
        finally:
            src_conn.close()

    def notify_mutation(self) -> Optional[Path]:
        """Call after a committed mutation. Creates a backup every N calls.

        Thread-safe: FastAPI runs sync routes in a worker thread pool, so
        concurrent mutations are possible even for a 2-user app.
        """
        if not self.backup_every_n_mutations:
            return None
        with self._lock:
            self._mutation_count += 1
            if self._mutation_count < self.backup_every_n_mutations:
                return None
            self._mutation_count = 0
        return self.create_backup()

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
