"""In-memory cache for the /insights payload.

Every /insights call re-embedded every unique description through fastembed
with no caching and recomputed recurring detection, forecasting, and every
other section from scratch -- at a few thousand unique descriptions the page
took many seconds on every visit. Past expenses don't change on their own,
so the whole payload is safe to cache per viewing user until either a
mutation happens (any expense/income create/update/delete, mode switch,
account deletion -- anything that calls audit_logger.log, see
services/audit.py's register_mutation_listener hook) or the calendar day
rolls over (several sections -- e.g. "days until due", month-to-date
figures -- are only correct as of "today").
"""
import threading

from services.audit import register_mutation_listener

_lock = threading.Lock()
_cache: dict[str, dict] = {}


def get(key: str) -> dict | None:
    with _lock:
        return _cache.get(key)


def put(key: str, value: dict) -> None:
    with _lock:
        _cache[key] = value


def clear() -> None:
    with _lock:
        _cache.clear()


register_mutation_listener(clear)
