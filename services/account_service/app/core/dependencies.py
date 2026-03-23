from collections.abc import Callable, Generator
from typing import cast

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..models.account import Account
from ..repositories.account_repository import AccountRepository
from .config import Settings
from .security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_session(request: Request) -> Generator[Session, None, None]:
    yield from request.app.state.database_manager.get_session()


def get_account_repository(session: Session = Depends(get_session)) -> AccountRepository:
    return AccountRepository(session)


def get_current_account(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
    repository: AccountRepository = Depends(get_account_repository),
) -> Account:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    payload = decode_access_token(credentials.credentials, settings)
    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token")

    account = repository.get_account_by_id(int(subject))
    if account is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found")

    return account


def require_roles(*roles: str) -> Callable[[Account], Account]:
    def dependency(account: Account = Depends(get_current_account)) -> Account:
        account_roles = {role.name for role in account.roles}
        if account_roles.isdisjoint(roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return account

    return dependency
