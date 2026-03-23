from dataclasses import dataclass
from typing import cast

import jwt
from fastapi import HTTPException, status

from .config import Settings


@dataclass(slots=True)
class AuthContext:
    subject: int
    username: str
    roles: list[str]


class TokenError(HTTPException):
    def __init__(self, detail: str = "Invalid token") -> None:
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def decode_access_token(token: str, settings: Settings) -> AuthContext:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise TokenError() from exc

    if payload.get("type") != "access":
        raise TokenError()

    subject = payload.get("sub")
    username = payload.get("username")
    roles = payload.get("roles", [])
    if not isinstance(subject, str) or not isinstance(username, str) or not isinstance(roles, list):
        raise TokenError()

    return AuthContext(subject=int(subject), username=username, roles=cast(list[str], roles))
