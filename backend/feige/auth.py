from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
import time

from fastapi import Request

from backend.feige.database import hash_password


SESSION_COOKIE = "feige_admin_session"
CSRF_COOKIE = "csrf_token"


def verify_password(password: str, digest: str, salt: str) -> bool:
    candidate, _ = hash_password(password, salt)
    return hmac.compare_digest(candidate, digest)


def make_session_token(secret: str, username: str) -> str:
    expires = int(time.time()) + 12 * 60 * 60
    payload = f"{username}|{expires}"
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}|{signature}"


def read_session_token(secret: str, token: str | None) -> str | None:
    if not token or token.count("|") != 2:
        return None
    username, expires_text, signature = token.split("|")
    try:
        expires = int(expires_text)
    except ValueError:
        return None
    if expires < int(time.time()):
        return None
    payload = f"{username}|{expires_text}"
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    return username


def authenticate(
    connection: sqlite3.Connection,
    username: str,
    password: str,
) -> sqlite3.Row | None:
    row = connection.execute(
        """
        SELECT username, password_hash, password_salt
        FROM admin_accounts WHERE username = ?
        """,
        (username,),
    ).fetchone()
    if not row or not verify_password(
        password,
        row["password_hash"],
        row["password_salt"],
    ):
        return None
    return row


def require_admin(request: Request, secret: str) -> str:
    from fastapi import HTTPException

    username = read_session_token(
        secret,
        request.cookies.get(SESSION_COOKIE),
    )
    if not username:
        raise HTTPException(status_code=401, detail="请先登录")
    return username


def require_csrf(request: Request) -> None:
    from fastapi import HTTPException

    cookie_token = request.cookies.get(CSRF_COOKIE, "")
    header_token = request.headers.get("X-CSRF-Token", "")
    if not cookie_token or not hmac.compare_digest(cookie_token, header_token):
        raise HTTPException(status_code=403, detail="CSRF 校验失败")


def new_csrf_token() -> str:
    return secrets.token_urlsafe(24)
