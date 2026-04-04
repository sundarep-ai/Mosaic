import hashlib
import hmac
import json
import os
import re
import time
from pathlib import Path

import bcrypt

from fastapi import APIRouter, HTTPException, Request, Response, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import (
    USER_A, USER_B,
    USER_A_LOGIN, USER_B_LOGIN,
    USER_A_PASSWORD, USER_B_PASSWORD,
    SECRET_KEY,
)

AVATARS_DIR = os.path.join(os.path.dirname(__file__), "uploads", "avatars")
os.makedirs(AVATARS_DIR, exist_ok=True)
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB

MAGIC_BYTES = {
    ".jpg":  [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    ".png":  [b"\x89PNG"],
    ".gif":  [b"GIF87a", b"GIF89a"],
    ".webp": [b"RIFF"],
}

_SAFE_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")

router = APIRouter()

# Maps login username -> password
USERS = {
    USER_A_LOGIN: USER_A_PASSWORD,
    USER_B_LOGIN: USER_B_PASSWORD,
}

# Maps login username -> display name
LOGIN_TO_DISPLAY = {
    USER_A_LOGIN: USER_A,
    USER_B_LOGIN: USER_B,
}


def hash_password(plain: str) -> str:
    """Generate a bcrypt hash for a plaintext password. Use for .env setup."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _check_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except (ValueError, TypeError):
        return False


def _validate_magic(data: bytes, ext: str) -> bool:
    """Verify file content magic bytes match the claimed extension."""
    signatures = MAGIC_BYTES.get(ext, [])
    for sig in signatures:
        if data[: len(sig)] == sig:
            if ext == ".webp":
                return len(data) >= 12 and data[8:12] == b"WEBP"
            return True
    return False


SESSION_COOKIE = "tallyus_session"
SESSION_TTL = 60 * 60 * 8  # 8 hours


def _sign(payload: str) -> str:
    return hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()


def _make_token(username: str) -> str:
    payload = json.dumps({"user": username, "ts": int(time.time())})
    sig = _sign(payload)
    return f"{payload}|{sig}"


def _verify_token(token: str) -> str | None:
    parts = token.rsplit("|", 1)
    if len(parts) != 2:
        return None
    payload, sig = parts
    if not hmac.compare_digest(_sign(payload), sig):
        return None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if data.get("user") not in USERS:
        return None
    if time.time() - data.get("ts", 0) > SESSION_TTL:
        return None
    return data["user"]


def get_current_user(request: Request) -> str:
    """Returns the login username of the authenticated user."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    username = _verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid session")
    return username


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/auth/login")
def login(data: LoginRequest, response: Response):
    # In solo mode, reject USER_B
    from database import engine
    from config import get_app_mode, USER_A_LOGIN
    from sqlmodel import Session as SqlSession
    with SqlSession(engine) as sess:
        mode = get_app_mode(sess)
    if mode == "solo" and data.username != USER_A_LOGIN:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    expected_password = USERS.get(data.username)
    if not expected_password or not _check_password(data.password, expected_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = _make_token(data.username)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
    )
    return {
        "username": data.username,
        "display_name": LOGIN_TO_DISPLAY.get(data.username, data.username),
        "user_map": {login: display for login, display in LOGIN_TO_DISPLAY.items()},
    }


@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(key=SESSION_COOKIE)
    return {"ok": True}


@router.get("/auth/me")
def get_me(request: Request):
    username = get_current_user(request)
    return {
        "username": username,
        "display_name": LOGIN_TO_DISPLAY.get(username, username),
        "user_map": {login: display for login, display in LOGIN_TO_DISPLAY.items()},
    }


def _find_avatar(username: str) -> str | None:
    """Return the path to an existing avatar file for the given username, or None."""
    for ext in ALLOWED_EXTENSIONS:
        path = os.path.join(AVATARS_DIR, f"{username}{ext}")
        if os.path.isfile(path):
            return path
    return None


@router.post("/auth/avatar")
async def upload_avatar(request: Request, file: UploadFile = File(...)):
    username = get_current_user(request)

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type not allowed. Use: {', '.join(ALLOWED_EXTENSIONS)}")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 2 MB.")

    if not _validate_magic(contents, ext):
        raise HTTPException(
            status_code=400,
            detail="File content does not match the declared file type.",
        )

    if not _SAFE_USERNAME_RE.match(username):
        raise HTTPException(status_code=400, detail="Invalid username format.")

    dest_path = Path(AVATARS_DIR).resolve() / f"{username}{ext}"
    if dest_path.parent != Path(AVATARS_DIR).resolve():
        raise HTTPException(status_code=400, detail="Invalid file path.")

    # Remove any existing avatar for this user
    existing = _find_avatar(username)
    if existing:
        os.remove(existing)

    dest = str(dest_path)
    with open(dest, "wb") as f:
        f.write(contents)

    return {"ok": True}


@router.get("/auth/avatar/{username}")
def get_avatar(username: str):
    if username not in USERS:
        raise HTTPException(status_code=404, detail="User not found")
    path = _find_avatar(username)
    if not path:
        raise HTTPException(status_code=404, detail="No avatar uploaded")
    return FileResponse(path)
