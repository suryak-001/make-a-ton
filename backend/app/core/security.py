"""Owner: B — password policy/hashing and signed session cookies."""

import hashlib
import re
import secrets

import bcrypt
from fastapi import Response
from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.config import settings

SESSION_COOKIE = "brightloop_session"
_serializer = URLSafeTimedSerializer(settings.session_secret, salt="session")


def password_problems(password: str) -> list[str]:
    """Brief: more than eight characters, with an uppercase letter, a lowercase letter and a special character."""
    problems = []
    if len(password) <= 8:
        problems.append("Must be more than 8 characters.")
    if not re.search(r"[a-z]", password):
        problems.append("Must contain a lowercase letter.")
    if not re.search(r"[A-Z]", password):
        problems.append("Must contain an uppercase letter.")
    if not re.search(r"[^A-Za-z0-9]", password):
        problems.append("Must contain a special character.")
    return problems


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def sign_session(user_id: int) -> str:
    return _serializer.dumps(user_id)


def read_session(token: str | None) -> int | None:
    if not token:
        return None
    try:
        return _serializer.loads(token, max_age=settings.session_max_age_seconds)
    except BadSignature:
        return None


def set_session_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        sign_session(user_id),
        max_age=settings.session_max_age_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


def new_reset_token() -> tuple[str, str]:
    """(token to email, sha256 to store). Only the hash is kept, so a leaked DB can't reset passwords."""
    token = secrets.token_urlsafe(32)
    return token, hash_reset_token(token)


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
