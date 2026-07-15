import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from models import Expense, Income

logger = logging.getLogger("mosaic")

# Process-wide listeners notified after ANY AuditLogger instance writes an
# entry (e.g. insights-cache invalidation, services/insights_cache.py).
# Module-level rather than a per-instance list because each route module
# binds its own `audit_logger` reference at import time and tests
# monkeypatch that per-module reference to a fresh instance per test (see
# tests/conftest.py's `audit_log` fixture) -- a per-instance list would
# silently stop firing the moment a module's audit_logger got swapped out.
_mutation_listeners: list[Callable[[], None]] = []


def register_mutation_listener(fn: Callable[[], None]) -> None:
    """Subscribe to be notified after every successful audit log write,
    regardless of which AuditLogger instance performed it."""
    _mutation_listeners.append(fn)


def expense_to_dict(expense: Expense) -> dict:
    """Serialize an Expense instance to a plain dict suitable for JSON."""
    return expense.model_dump()


def income_to_dict(income: Income) -> dict:
    """Serialize an Income instance to a plain dict suitable for JSON."""
    return income.model_dump()


class AuditLogger:
    """Append-only JSONL audit log for expense mutations.

    This is best-effort, not a ledger: a full disk or permissions error is
    swallowed (logged to the app logger, not raised) so a broken audit log
    never blocks a real mutation that already committed to the database.
    There is no restore/replay tool, so a write failure here is a silent gap
    between the DB and its audit trail — acceptable for this app's threat
    model (accidental/destructive-mutation forensics), not acceptable if you
    need a strict, tamper-evident record.
    """

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.log_dir / "audit.jsonl"
        # Optional callback invoked after a successful write, wired up by the
        # app's startup lifespan to trigger backups on a mutation cadence
        # rather than only once at process startup (see services/backup.py).
        self.on_mutation = None

    def log(
        self,
        operation: str,
        user: str,
        data: dict,
        before: dict | None = None,
    ) -> None:
        """Append a single audit entry. Never raises -- logs errors instead."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "user": user,
            "data": data,
        }
        if before is not None:
            entry["before"] = before

        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception:
            logger.exception("Failed to write audit log entry: %s", entry)
            return

        if self.on_mutation:
            try:
                self.on_mutation()
            except Exception:
                logger.exception("Backup-trigger callback failed after audit log write")

        for listener in _mutation_listeners:
            try:
                listener()
            except Exception:
                logger.exception("Mutation listener failed after audit log write")


# Module-level singleton -- initialized with default path.
# Import and use directly: from services.audit import audit_logger, expense_to_dict
import os as _os
_data_dir = Path(_os.getenv("DATA_DIR", str(Path(__file__).parent.parent)))
_default_dir = _data_dir / "audit"
audit_logger = AuditLogger(_default_dir)
