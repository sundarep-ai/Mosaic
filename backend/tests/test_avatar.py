"""Tests for avatar upload/retrieval — magic-byte validation, size limits,
and stale-extension cleanup (bucket 08, item 8; previously zero coverage).

AVATARS_DIR defaults to a real on-disk directory under the backend package
(see database.DATA_DIR) rather than a pytest tmp_path, since it's resolved
once at import time from the production DATA_DIR default. Every test here
monkeypatches auth.AVATARS_DIR to a tmp_path so nothing actually writes into
the real checkout on disk.
"""

import os

from conftest import USER_A_LOGIN

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG_BYTES = b"\xff\xd8\xff" + b"\x00" * 64


def _use_tmp_avatars_dir(monkeypatch, tmp_path):
    import auth as auth_mod
    avatar_dir = tmp_path / "avatars"
    avatar_dir.mkdir()
    monkeypatch.setattr(auth_mod, "AVATARS_DIR", str(avatar_dir))
    return avatar_dir


def test_avatar_upload_accepts_valid_png(auth_client_a, monkeypatch, tmp_path):
    avatar_dir = _use_tmp_avatars_dir(monkeypatch, tmp_path)

    resp = auth_client_a.post(
        "/api/auth/avatar",
        files={"file": ("avatar.png", PNG_BYTES, "image/png")},
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert (avatar_dir / f"{USER_A_LOGIN}.png").exists()


def test_avatar_upload_rejects_disallowed_extension(auth_client_a, monkeypatch, tmp_path):
    _use_tmp_avatars_dir(monkeypatch, tmp_path)

    resp = auth_client_a.post(
        "/api/auth/avatar",
        files={"file": ("shell.exe", b"MZ" + b"\x00" * 64, "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert "not allowed" in resp.json()["detail"]


def test_avatar_upload_rejects_magic_byte_mismatch(auth_client_a, monkeypatch, tmp_path):
    """A file renamed to .png that isn't actually PNG content must be
    rejected — the extension alone is never trusted."""
    _use_tmp_avatars_dir(monkeypatch, tmp_path)

    resp = auth_client_a.post(
        "/api/auth/avatar",
        files={"file": ("fake.png", b"not actually a png" + b"\x00" * 64, "image/png")},
    )
    assert resp.status_code == 400
    assert "does not match" in resp.json()["detail"]


def test_avatar_upload_rejects_oversized_file(auth_client_a, monkeypatch, tmp_path):
    import auth as auth_mod
    _use_tmp_avatars_dir(monkeypatch, tmp_path)

    oversized = PNG_BYTES + b"\x00" * auth_mod.MAX_FILE_SIZE
    resp = auth_client_a.post(
        "/api/auth/avatar",
        files={"file": ("avatar.png", oversized, "image/png")},
    )
    assert resp.status_code == 400
    assert "too large" in resp.json()["detail"].lower()


def test_avatar_upload_replaces_old_extension(auth_client_a, monkeypatch, tmp_path):
    """Uploading a .jpg after a previously-uploaded .png must remove the
    stale .png — otherwise both would exist and _find_avatar's fixed
    extension-preference order would silently keep serving the old one."""
    avatar_dir = _use_tmp_avatars_dir(monkeypatch, tmp_path)

    first = auth_client_a.post(
        "/api/auth/avatar", files={"file": ("avatar.png", PNG_BYTES, "image/png")},
    )
    assert first.status_code == 200
    assert (avatar_dir / f"{USER_A_LOGIN}.png").exists()

    second = auth_client_a.post(
        "/api/auth/avatar", files={"file": ("avatar.jpg", JPEG_BYTES, "image/jpeg")},
    )
    assert second.status_code == 200
    assert (avatar_dir / f"{USER_A_LOGIN}.jpg").exists()
    assert not (avatar_dir / f"{USER_A_LOGIN}.png").exists()


def test_get_avatar_returns_404_when_none_uploaded(auth_client_a, monkeypatch, tmp_path):
    _use_tmp_avatars_dir(monkeypatch, tmp_path)
    resp = auth_client_a.get(f"/api/auth/avatar/{USER_A_LOGIN}")
    assert resp.status_code == 404


def test_get_avatar_returns_file_when_uploaded(auth_client_a, monkeypatch, tmp_path):
    avatar_dir = _use_tmp_avatars_dir(monkeypatch, tmp_path)
    auth_client_a.post("/api/auth/avatar", files={"file": ("avatar.png", PNG_BYTES, "image/png")})

    resp = auth_client_a.get(f"/api/auth/avatar/{USER_A_LOGIN}")
    assert resp.status_code == 200
    assert resp.content == PNG_BYTES


def test_get_avatar_returns_404_for_unknown_user(auth_client_a, monkeypatch, tmp_path):
    _use_tmp_avatars_dir(monkeypatch, tmp_path)
    resp = auth_client_a.get("/api/auth/avatar/nobody")
    assert resp.status_code == 404
