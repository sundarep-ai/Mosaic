import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from models import Expense

logger = logging.getLogger("mosaic")


def expense_to_dict(expense: Expense) -> dict:
    """Serialize an Expense instance to a plain dict suitable for JSON."""
    return expense.model_dump()


class AuditLogger:
    """Append-only JSONL audit log for expense mutations."""

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.log_dir / "audit.jsonl"

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


# Module-level singleton -- initialized with default path.
# Import and use directly: from services.audit import audit_logger, expense_to_dict
import os as _os
_data_dir = Path(_os.getenv("DATA_DIR", str(Path(__file__).parent.parent)))
_default_dir = _data_dir / "audit"
audit_logger = AuditLogger(_default_dir)
