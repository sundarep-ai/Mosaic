import hashlib
import hmac
import json
import time

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from config import (
    USER_A, USER_B,
    USER_A_LOGIN, USER_B_LOGIN,
    USER_A_PASSWORD, USER_B_PASSWORD,
    SECRET_KEY,
)

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

SESSION_COOKIE = "tallyus_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


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
    expected_password = USERS.get(data.username)
    if not expected_password or data.password != expected_password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = _make_token(data.username)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_MAX_AGE,
    )
    return {
        "username": data.username,
        "display_name": LOGIN_TO_DISPLAY.get(data.username, data.username),
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
    }
