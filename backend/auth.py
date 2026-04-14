import collections
import hashlib
import hmac
import json
import os
import re
import tempfile
import threading
import time
from pathlib import Path

import bcrypt

from fastapi import APIRouter, HTTPException, Request, Response, UploadFile, File, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import Session

from config import SECRET_KEY
import database
from database import get_session
from models import User
from users import get_user_by_username, get_user_count, build_user_map, is_primary_user

IS_DEV = os.getenv("ENV", "development") == "development"

# COOKIE_SECURE: override the automatic dev/prod detection when needed.
# Set COOKIE_SECURE=false explicitly for production HTTP (local network) deployments.
_cookie_secure_env = os.getenv("COOKIE_SECURE")
if _cookie_secure_env is not None:
    COOKIE_SECURE = _cookie_secure_env.lower() in ("true", "1", "yes")
else:
    COOKIE_SECURE = not IS_DEV

from database import DATA_DIR as _DATA_DIR
AVATARS_DIR = str(_DATA_DIR / "uploads" / "avatars")
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
_SAFE_DISPLAY_NAME_RE = re.compile(r"^[a-zA-Z0-9 '\-\.À-ÖØ-öø-ÿ]+$")

SECURITY_QUESTIONS = [
    "What was the name of your first pet?",
    "What city were you born in?",
    "What was your childhood nickname?",
    "What is the name of your favorite teacher?",
    "What was the make of your first car?",
]

router = APIRouter()


def hash_password(plain: str) -> str:
    """Generate a bcrypt hash for a plaintext password."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _check_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except (ValueError, TypeError):
        return False


def _hash_answer(answer: str) -> str:
    """Normalize and hash a security answer."""
    normalized = answer.strip().lower()
    return bcrypt.hashpw(normalized.encode(), bcrypt.gensalt()).decode()


def _check_answer(answer: str, hashed: str) -> bool:
    """Verify a security answer against its hash."""
    normalized = answer.strip().lower()
    try:
        return bcrypt.checkpw(normalized.encode(), hashed.encode())
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


SESSION_COOKIE = "mosaic_session"
SESSION_TTL = 60 * 60 * 8  # 8 hours
PERSISTENT_TTL = 60 * 60 * 24 * 365  # 1 year


def _sign(payload: str) -> str:
    return hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()


def _make_token(username: str, persist: bool = False, session_version: int = 0) -> str:
    payload = json.dumps({"user": username, "ts": int(time.time()), "persist": persist, "sv": session_version})
    sig = _sign(payload)
    return f"{payload}|{sig}"


def _verify_token(token: str, session: Session | None = None) -> str | None:
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

    username = data.get("user")
    if not username:
        return None

    # Check if user still exists in DB and validate session version
    if session is not None:
        user = get_user_by_username(session, username)
    else:
        with Session(database.engine) as s:
            user = get_user_by_username(s, username)
    if not user:
        return None
    if data.get("sv", 0) != user.session_version:
        return None

    ttl = PERSISTENT_TTL if data.get("persist", False) else SESSION_TTL
    if time.time() - data.get("ts", 0) > ttl:
        return None

    return username


def get_current_user(request: Request, session: Session = Depends(get_session)) -> str:
    """Returns the login username of the authenticated user."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    username = _verify_token(token, session=session)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid session")
    return username


# ── Forgot-password rate limiter (CR-2) ──────────────────────────────

_reset_attempts: dict[str, list[float]] = collections.defaultdict(list)
_reset_lock = threading.Lock()
RESET_MAX_ATTEMPTS = 5
RESET_WINDOW_SECONDS = 300  # 5 minutes


def _check_reset_rate_limit(username: str) -> None:
    now = time.time()
    with _reset_lock:
        attempts = [t for t in _reset_attempts[username] if now - t < RESET_WINDOW_SECONDS]
        _reset_attempts[username] = attempts
        if len(attempts) >= RESET_MAX_ATTEMPTS:
            raise HTTPException(status_code=429, detail="Too many attempts. Try again in 5 minutes.")


def _record_reset_failure(username: str) -> None:
    with _reset_lock:
        _reset_attempts[username].append(time.time())


def _clear_reset_attempts(username: str) -> None:
    with _reset_lock:
        _reset_attempts.pop(username, None)


# ── Registration ──────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    username: str
    display_name: str
    password: str
    security_question: str
    security_answer: str


@router.post("/auth/register", status_code=201)
def register(data: RegisterRequest, response: Response, session: Session = Depends(get_session)):
    # Validate username format
    if not _SAFE_USERNAME_RE.match(data.username):
        raise HTTPException(status_code=422, detail="Username must be alphanumeric (underscores and hyphens allowed)")
    if len(data.username) < 2 or len(data.username) > 50:
        raise HTTPException(status_code=422, detail="Username must be 2-50 characters")

    # Validate display name format
    if not _SAFE_DISPLAY_NAME_RE.match(data.display_name):
        raise HTTPException(status_code=422, detail="Display name may only contain letters, numbers, spaces, apostrophes, hyphens, and periods")
    if len(data.display_name) < 2 or len(data.display_name) > 100:
        raise HTTPException(status_code=422, detail="Display name must be 2-100 characters")

    # Validate password
    if len(data.password) < 6:
        raise HTTPException(status_code=422, detail="Password must be at least 6 characters")
    if len(data.password) > 128:
        raise HTTPException(status_code=422, detail="Password must be 128 characters or fewer")

    # Validate security question
    if not data.security_question or len(data.security_question) > 300:
        raise HTTPException(status_code=422, detail="Security question is required (max 300 characters)")

    # Validate security answer
    if not data.security_answer.strip():
        raise HTTPException(status_code=422, detail="Security answer is required")

    # Check user cap
    count = get_user_count(session)
    if count >= 2:
        raise HTTPException(status_code=409, detail="Maximum of 2 accounts allowed")

    # Check uniqueness
    if get_user_by_username(session, data.username):
        raise HTTPException(status_code=409, detail="Username already taken")
    from users import get_user_by_display_name
    if get_user_by_display_name(session, data.display_name):
        raise HTTPException(status_code=409, detail="Display name already taken")

    user = User(
        username=data.username,
        display_name=data.display_name,
        password_hash=hash_password(data.password),
        security_question=data.security_question,
        security_answer_hash=_hash_answer(data.security_answer),
    )
    session.add(user)

    # First user → ensure mode is set to personal
    if count == 0:
        from models import Settings
        settings = session.get(Settings, 1)
        if settings:
            settings.app_mode = "personal"
        else:
            settings = Settings(id=1, app_mode="personal")
        session.add(settings)

    # Second user → automatically switch mode to shared so both users can log in immediately
    if count == 1:
        from models import Settings
        settings = session.get(Settings, 1)
        if settings:
            settings.app_mode = "shared"
        else:
            settings = Settings(id=1, app_mode="shared")
        session.add(settings)

    session.commit()
    session.refresh(user)

    # Auto-login
    token = _make_token(user.username, session_version=user.session_version)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        max_age=SESSION_TTL,
    )
    return {
        "username": user.username,
        "display_name": user.display_name,
        "user_map": build_user_map(session),
    }


@router.get("/auth/account-status")
def account_status(session: Session = Depends(get_session)):
    """Public endpoint: how many accounts exist, is registration open?"""
    count = get_user_count(session)
    return {"user_count": count, "registration_open": count < 2}


@router.get("/auth/security-questions")
def list_security_questions():
    """Return the preset security questions."""
    return {"questions": SECURITY_QUESTIONS}


# ── Login / Logout / Me ──────────────────────────────────────────────


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/auth/login")
def login(data: LoginRequest, response: Response, session: Session = Depends(get_session)):
    from config import get_app_mode
    mode = get_app_mode(session)

    # In personal mode, only the first-created user can log in
    if mode == "personal" and not is_primary_user(session, data.username):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    user = get_user_by_username(session, data.username)
    if not user or not _check_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    persist = user.stay_signed_in
    token = _make_token(data.username, persist=persist, session_version=user.session_version)
    ttl = PERSISTENT_TTL if persist else SESSION_TTL

    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        max_age=ttl,
    )
    return {
        "username": user.username,
        "display_name": user.display_name,
        "user_map": build_user_map(session),
    }


@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(key=SESSION_COOKIE)
    return {"ok": True}


@router.get("/auth/me")
def get_me(request: Request, session: Session = Depends(get_session)):
    username = get_current_user(request, session)
    user = get_user_by_username(session, username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return {
        "username": user.username,
        "display_name": user.display_name,
        "user_map": build_user_map(session),
        "stay_signed_in": user.stay_signed_in,
    }


# ── Forgot Password ──────────────────────────────────────────────────


class ForgotPasswordQuestionRequest(BaseModel):
    username: str


@router.post("/auth/forgot-password/question")
def forgot_password_question(data: ForgotPasswordQuestionRequest, session: Session = Depends(get_session)):
    user = get_user_by_username(session, data.username)
    if not user:
        # Return a plausible placeholder instead of null so attackers can't
        # enumerate valid usernames by checking whether this field is non-null.
        return {"security_question": SECURITY_QUESTIONS[0]}
    return {"security_question": user.security_question}


class ForgotPasswordResetRequest(BaseModel):
    username: str
    security_answer: str
    new_password: str


@router.post("/auth/forgot-password/reset")
def forgot_password_reset(data: ForgotPasswordResetRequest, session: Session = Depends(get_session)):
    _check_reset_rate_limit(data.username)

    user = get_user_by_username(session, data.username)
    if not user:
        # Record a failure and return 401 (same as wrong answer) so attackers
        # can't enumerate valid usernames via 404 vs 401 differences.
        _record_reset_failure(data.username)
        raise HTTPException(status_code=401, detail="Incorrect security answer")

    if not _check_answer(data.security_answer, user.security_answer_hash):
        _record_reset_failure(data.username)
        raise HTTPException(status_code=401, detail="Incorrect security answer")

    _clear_reset_attempts(data.username)

    if len(data.new_password) < 6:
        raise HTTPException(status_code=422, detail="Password must be at least 6 characters")
    if len(data.new_password) > 128:
        raise HTTPException(status_code=422, detail="Password must be 128 characters or fewer")

    user.password_hash = hash_password(data.new_password)
    user.session_version = (user.session_version or 0) + 1
    session.add(user)
    session.commit()
    return {"ok": True}


# ── Change Password ──────────────────────────────────────────────────


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.put("/auth/change-password")
def change_password(
    data: ChangePasswordRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    username = get_current_user(request, session)
    user = get_user_by_username(session, username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not _check_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    if len(data.new_password) < 6:
        raise HTTPException(status_code=422, detail="Password must be at least 6 characters")
    if len(data.new_password) > 128:
        raise HTTPException(status_code=422, detail="Password must be 128 characters or fewer")

    user.password_hash = hash_password(data.new_password)
    user.session_version = (user.session_version or 0) + 1
    session.add(user)
    session.commit()

    # Reissue a fresh token so the current session survives the version bump
    token = _make_token(username, persist=user.stay_signed_in, session_version=user.session_version)
    ttl = PERSISTENT_TTL if user.stay_signed_in else SESSION_TTL
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        max_age=ttl,
    )
    return {"ok": True}


# ── Stay Signed In ───────────────────────────────────────────────────


class StaySignedInRequest(BaseModel):
    enabled: bool


@router.put("/auth/stay-signed-in")
def update_stay_signed_in(
    data: StaySignedInRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    username = get_current_user(request, session)
    user = get_user_by_username(session, username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    user.stay_signed_in = data.enabled
    session.add(user)
    session.commit()

    # Reissue token with updated persistence
    token = _make_token(username, persist=data.enabled, session_version=user.session_version)
    ttl = PERSISTENT_TTL if data.enabled else SESSION_TTL
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        max_age=ttl,
    )
    return {"ok": True, "stay_signed_in": data.enabled}


# ── Account Deletion ─────────────────────────────────────────────────


class DeleteAccountRequest(BaseModel):
    password: str
    data_action: str  # "delete" or "anonymize"


@router.delete("/auth/account")
def delete_account(
    data: DeleteAccountRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    username = get_current_user(request, session)
    user = get_user_by_username(session, username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not _check_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect password")

    if data.data_action not in ("delete", "anonymize"):
        raise HTTPException(status_code=422, detail="data_action must be 'delete' or 'anonymize'")

    from models import Expense, Income, UserPreference, DismissedMerge, Settings
    from sqlmodel import select

    display_name = user.display_name

    if data.data_action == "delete":
        # Delete all expenses paid by this user
        expenses = session.exec(select(Expense).where(Expense.paid_by == display_name)).all()
        for e in expenses:
            session.delete(e)
        # Delete all income
        incomes = session.exec(select(Income).where(Income.user_id == username)).all()
        for i in incomes:
            session.delete(i)
    else:
        # Anonymize expenses
        expenses = session.exec(select(Expense).where(Expense.paid_by == display_name)).all()
        for e in expenses:
            e.paid_by = "Deleted User"
            if e.split_method == f"100% {display_name}":
                e.split_method = "Personal"
            session.add(e)
        # Anonymize income
        incomes = session.exec(select(Income).where(Income.user_id == username)).all()
        for i in incomes:
            i.user_id = "deleted"
            session.add(i)

    # Delete user preference
    prefs = session.exec(select(UserPreference).where(UserPreference.username == username)).all()
    for p in prefs:
        session.delete(p)

    # Delete dismissed merges by this user
    dismissals = session.exec(select(DismissedMerge).where(DismissedMerge.dismissed_by == username)).all()
    for d in dismissals:
        session.delete(d)

    # Delete avatar
    existing_avatar = _find_avatar(username)
    if existing_avatar:
        os.remove(existing_avatar)

    # Delete the user
    session.delete(user)

    # Count remaining users before the commit. The deleted user is still in the
    # DB at this point (session.delete queues the deletion; the row goes away on
    # commit), so we subtract 1 to get the post-commit count.
    remaining = get_user_count(session) - 1
    if remaining <= 1:
        settings = session.get(Settings, 1)
        if settings:
            settings.app_mode = "personal"
            session.add(settings)

    session.commit()

    response.delete_cookie(key=SESSION_COOKIE)
    return {"ok": True}


# ── Avatar ───────────────────────────────────────────────────────────


def _find_avatar(username: str) -> str | None:
    """Return the path to an existing avatar file for the given username, or None."""
    for ext in ALLOWED_EXTENSIONS:
        path = os.path.join(AVATARS_DIR, f"{username}{ext}")
        if os.path.isfile(path):
            return path
    return None


@router.post("/auth/avatar")
async def upload_avatar(
    request: Request,
    session: Session = Depends(get_session),
    file: UploadFile = File(...),
):
    username = get_current_user(request, session)

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type not allowed. Use: {', '.join(ALLOWED_EXTENSIONS)}")

    # Read one byte beyond the limit so we can distinguish "exactly at limit" from "over limit"
    # without loading an arbitrarily large file into memory first.
    contents = await file.read(MAX_FILE_SIZE + 1)
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

    # Atomic write: write to a temp file then rename over the destination
    tmp_fd, tmp_path = tempfile.mkstemp(dir=AVATARS_DIR)
    try:
        with os.fdopen(tmp_fd, "wb") as f:
            f.write(contents)
        os.replace(tmp_path, str(dest_path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    # Clean up any stale avatar with a different extension
    for old_ext in ALLOWED_EXTENSIONS:
        old = os.path.join(AVATARS_DIR, f"{username}{old_ext}")
        if old != str(dest_path) and os.path.isfile(old):
            os.remove(old)

    return {"ok": True}


@router.get("/auth/avatar/{username}")
def get_avatar(username: str, session: Session = Depends(get_session)):
    user = get_user_by_username(session, username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    path = _find_avatar(username)
    if not path:
        raise HTTPException(status_code=404, detail="No avatar uploaded")
    return FileResponse(path)
