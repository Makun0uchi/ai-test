from datetime import datetime, timedelta
from secrets import token_urlsafe
from typing import cast
from uuid import uuid4

import jwt
from fastapi import HTTPException, status
from passlib.context import CryptContext

from .config import Settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class TokenError(HTTPException):
    def __init__(self, detail: str = "Invalid token") -> None:
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def hash_password(password: str) -> str:
    return cast(str, pwd_context.hash(password))


def verify_password(password: str, password_hash: str) -> bool:
    return cast(bool, pwd_context.verify(password, password_hash))


def create_access_token(
    *,
    subject: int,
    username: str,
    roles: list[str],
    settings: Settings,
) -> str:
    expires_at = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(subject),
        "username": username,
        "roles": roles,
        "type": "access",
        "jti": str(uuid4()),
        "exp": expires_at,
    }
    return cast(str, jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm))


def decode_access_token(token: str, settings: Settings) -> dict[str, object]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise TokenError() from exc

    if payload.get("type") != "access":
        raise TokenError()

    return cast(dict[str, object], payload)


def generate_refresh_token() -> str:
    return token_urlsafe(48)


def refresh_token_expiry(settings: Settings) -> datetime:
    return datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
