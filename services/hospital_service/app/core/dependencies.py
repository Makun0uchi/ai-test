from collections.abc import Callable, Generator
from typing import cast

from fastapi import Depends, Header, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from libs.service_common.security import ensure_internal_token
from sqlalchemy.orm import Session

from .config import Settings
from .security import AuthContext, decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_session(request: Request) -> Generator[Session, None, None]:
    yield from request.app.state.database_manager.get_session()


def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> AuthContext:
    if credentials is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return decode_access_token(credentials.credentials, settings)


def require_roles(*roles: str) -> Callable[[AuthContext], AuthContext]:
    def dependency(principal: AuthContext = Depends(get_current_principal)) -> AuthContext:
        if set(principal.roles).isdisjoint(roles):
            from fastapi import HTTPException

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return principal

    return dependency


def require_internal_token(
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
    settings: Settings = Depends(get_settings),
) -> None:
    ensure_internal_token(x_internal_token, expected_token=settings.internal_api_key)
