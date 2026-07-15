"""Tests for backup cadence, verification, and the startup integrity gate
(bucket 05, item 2).

These construct BackupManager directly against real on-disk SQLite files —
independent of the shared in-memory API test database — since backups are
fundamentally a filesystem/on-disk-SQLite concern.
"""

import asyncio
import sqlite3

import pytest
from sqlmodel import SQLModel, Session, create_engine

from services.backup import BackupManager


def _make_real_db(tmp_path, name="mosaic.db"):
    """Create a real on-disk SQLite DB with the app's schema and one row."""
    db_path = tmp_path / name
    engine = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(engine)
    from models import User

    with Session(engine) as s:
        s.add(User(
            username="alice",
            display_name="Alice",
            password_hash="x",
            security_question="q",
            security_answer_hash="x",
        ))
        s.commit()
    engine.dispose()
    return db_path


# ── Verification ──────────────────────────────────────────────────────────────


def test_create_backup_produces_a_verifiable_copy(tmp_path):
    db_path = _make_real_db(tmp_path)
    backup_dir = tmp_path / "backups"
    mgr = BackupManager(db_path=db_path, audit_log_path=tmp_path / "audit.jsonl", backup_dir=backup_dir)

    dest = mgr.create_backup()

    assert (dest / "mosaic.db").exists()
    assert mgr.verify_backup(dest) is True

    conn = sqlite3.connect(str(dest / "mosaic.db"))
    try:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert conn.execute("SELECT COUNT(*) FROM user").fetchone()[0] == 1
    finally:
        conn.close()


def test_verify_backup_detects_row_count_mismatch(tmp_path):
    db_path = _make_real_db(tmp_path)
    backup_dir = tmp_path / "backups"
    mgr = BackupManager(db_path=db_path, audit_log_path=tmp_path / "audit.jsonl", backup_dir=backup_dir)

    dest = mgr.create_backup()
    assert mgr.verify_backup(dest) is True

    # Simulate drift: a row lands in the source after the backup completed.
    engine = create_engine(f"sqlite:///{db_path}")
    from models import User
    with Session(engine) as s:
        s.add(User(
            username="bob", display_name="Bob", password_hash="x",
            security_question="q", security_answer_hash="x",
        ))
        s.commit()
    engine.dispose()

    assert mgr.verify_backup(dest) is False


def test_verify_backup_detects_corruption(tmp_path):
    db_path = _make_real_db(tmp_path)
    backup_dir = tmp_path / "backups"
    mgr = BackupManager(db_path=db_path, audit_log_path=tmp_path / "audit.jsonl", backup_dir=backup_dir)

    dest = mgr.create_backup()
    # Corrupt the backup copy directly (not the source).
    with open(dest / "mosaic.db", "r+b") as f:
        f.seek(100)
        f.write(b"\xff" * 50)

    assert mgr.verify_backup(dest) is False


def test_verify_backup_missing_file_returns_false(tmp_path):
    db_path = _make_real_db(tmp_path)
    backup_dir = tmp_path / "backups"
    mgr = BackupManager(db_path=db_path, audit_log_path=tmp_path / "audit.jsonl", backup_dir=backup_dir)
    dest = backup_dir / "2026-01-01T000000"
    dest.mkdir(parents=True)
    assert mgr.verify_backup(dest) is False


# ── Rotation / retention ───────────────────────────────────────────────────────


def test_rotate_backups_respects_max_backups(tmp_path):
    db_path = _make_real_db(tmp_path)
    backup_dir = tmp_path / "backups"
    mgr = BackupManager(db_path=db_path, audit_log_path=tmp_path / "audit.jsonl", backup_dir=backup_dir, max_backups=3)

    for _ in range(5):
        mgr.create_backup()

    remaining = [d for d in backup_dir.iterdir() if d.is_dir()]
    assert len(remaining) == 3


def test_rotate_backups_never_touches_non_matching_entries(tmp_path):
    """_rotate_backups deletes directories via shutil.rmtree selected purely
    by regex-matching their name (bucket 08, item 8 — "the regex-driven
    shutil.rmtree where a bug deletes directories"). A directory or file
    that doesn't match the timestamp pattern must survive rotation even
    when it sits right next to backups that get pruned, and even when
    rotation has more than enough matching candidates to hit max_backups
    without ever needing to touch them."""
    db_path = _make_real_db(tmp_path)
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    # A stray non-backup directory and file that happen to live alongside
    # real backups — must never be considered rotation candidates.
    stray_dir = backup_dir / "user-uploads"
    stray_dir.mkdir()
    (stray_dir / "keepme.txt").write_text("not a backup")
    stray_file = backup_dir / "README.txt"
    stray_file.write_text("not a backup either")
    # A directory that's *almost* a timestamp but doesn't fully match the
    # anchored pattern (extra suffix) — must also survive.
    almost_match = backup_dir / "2026-01-01T010101-notes"
    almost_match.mkdir()

    mgr = BackupManager(db_path=db_path, audit_log_path=tmp_path / "audit.jsonl", backup_dir=backup_dir, max_backups=2)
    for _ in range(4):
        mgr.create_backup()

    assert stray_dir.is_dir()
    assert (stray_dir / "keepme.txt").exists()
    assert stray_file.exists()
    assert almost_match.is_dir()

    real_backups = [d for d in backup_dir.iterdir() if d.is_dir() and d not in (stray_dir, almost_match)]
    assert len(real_backups) == 2


def test_main_uses_a_single_deliberate_max_backups_default():
    """main.py previously hardcoded max_backups=1000 while BackupManager's own
    default was 10, and nothing enforced which was in effect. Pin the single
    deliberate value main.py now uses.
    """
    import main
    assert main.MAX_BACKUPS == 30
    assert main.MAX_BACKUPS != 1000


# ── Mutation-triggered backups ─────────────────────────────────────────────────


def test_notify_mutation_backs_up_every_n_calls(tmp_path):
    db_path = _make_real_db(tmp_path)
    backup_dir = tmp_path / "backups"
    mgr = BackupManager(
        db_path=db_path, audit_log_path=tmp_path / "audit.jsonl",
        backup_dir=backup_dir, backup_every_n_mutations=3,
    )

    assert mgr.notify_mutation() is None
    assert mgr.notify_mutation() is None
    result = mgr.notify_mutation()
    assert result is not None
    assert (result / "mosaic.db").exists()

    # Counter resets — doesn't fire again until 3 more mutations.
    assert mgr.notify_mutation() is None
    assert mgr.notify_mutation() is None
    assert mgr.notify_mutation() is not None


def test_notify_mutation_disabled_when_not_configured(tmp_path):
    db_path = _make_real_db(tmp_path)
    mgr = BackupManager(db_path=db_path, audit_log_path=tmp_path / "audit.jsonl", backup_dir=tmp_path / "backups")
    for _ in range(10):
        assert mgr.notify_mutation() is None


def test_audit_logger_on_mutation_hook_triggers_backup(tmp_path):
    """AuditLogger.log() calls the on_mutation callback after a successful write."""
    from services.audit import AuditLogger

    calls = []
    logger = AuditLogger(tmp_path / "audit")
    logger.on_mutation = lambda: calls.append(1)

    logger.log("CREATE", "alice", {"id": 1})
    assert calls == [1]


def test_audit_logger_on_mutation_failure_does_not_raise(tmp_path):
    from services.audit import AuditLogger

    def _boom():
        raise RuntimeError("backup failed")

    logger = AuditLogger(tmp_path / "audit")
    logger.on_mutation = _boom
    logger.log("CREATE", "alice", {"id": 1})  # must not raise


# ── Startup integrity gate ─────────────────────────────────────────────────────


def test_check_db_integrity_detects_corruption(tmp_path, monkeypatch):
    import database

    db_path = tmp_path / "corrupt.db"
    db_path.write_bytes(b"not a real sqlite file" + b"\x00" * 100)

    corrupt_engine = create_engine(f"sqlite:///{db_path}")
    monkeypatch.setattr(database, "engine", corrupt_engine)

    assert database.check_db_integrity() is False
    corrupt_engine.dispose()


def test_lifespan_refuses_to_start_when_integrity_check_fails(monkeypatch):
    import main

    monkeypatch.setattr(main, "check_db_integrity", lambda: False)

    backup_calls = []
    monkeypatch.setattr(
        "services.backup.BackupManager.create_backup",
        lambda self: backup_calls.append(1),
    )

    async def _run():
        async with main.lifespan(main.app):
            pass

    with pytest.raises(RuntimeError, match="integrity check FAILED"):
        asyncio.run(_run())

    assert backup_calls == []  # must not attempt a backup of a DB that failed its check
