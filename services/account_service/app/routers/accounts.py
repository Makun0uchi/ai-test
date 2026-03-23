from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from ..core.dependencies import get_account_repository, get_current_account, require_roles
from ..models.account import Account
from ..repositories.account_repository import AccountRepository
from ..schemas.account import (
    AccountResponse,
    AdminCreateAccountRequest,
    AdminUpdateAccountRequest,
    UpdateCurrentAccountRequest,
)
from ..services.account_service import AccountService

router = APIRouter(prefix="/api/Accounts", tags=["accounts"])
AdminAccount = Annotated[Account, Depends(require_roles("Admin"))]


@router.get("/Me", response_model=AccountResponse)
def get_me(
    current_account: Account = Depends(get_current_account),
    repository: AccountRepository = Depends(get_account_repository),
) -> AccountResponse:
    return AccountService(repository).get_me(current_account)


@router.put("/Update", response_model=AccountResponse)
def update_me(
    payload: UpdateCurrentAccountRequest,
    current_account: Account = Depends(get_current_account),
    repository: AccountRepository = Depends(get_account_repository),
) -> AccountResponse:
    return AccountService(repository).update_me(current_account, payload)


@router.get("", response_model=list[AccountResponse])
def list_accounts(
    _: AdminAccount,
    repository: AccountRepository = Depends(get_account_repository),
    from_: int = Query(default=0, alias="from", ge=0),
    count: int = Query(default=20, alias="count", ge=1, le=100),
) -> list[AccountResponse]:
    return AccountService(repository).list_accounts(from_, count)


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AdminCreateAccountRequest,
    _: AdminAccount,
    repository: AccountRepository = Depends(get_account_repository),
) -> AccountResponse:
    return AccountService(repository).create_account(payload)


@router.put("/{account_id}", response_model=AccountResponse)
def update_account(
    account_id: int,
    payload: AdminUpdateAccountRequest,
    _: AdminAccount,
    repository: AccountRepository = Depends(get_account_repository),
) -> AccountResponse:
    return AccountService(repository).update_account(account_id, payload)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: int,
    _: AdminAccount,
    repository: AccountRepository = Depends(get_account_repository),
) -> Response:
    AccountService(repository).delete_account(account_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
