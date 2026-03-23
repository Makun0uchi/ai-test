from typing import Annotated

from fastapi import APIRouter, Depends

from ..core.dependencies import get_account_repository, require_internal_token
from ..repositories.account_repository import AccountRepository
from ..schemas.internal import InternalAccountResponse
from ..services.account_service import AccountService

router = APIRouter(prefix="/internal/accounts", tags=["internal"])
InternalPrincipal = Annotated[None, Depends(require_internal_token)]


@router.get("/{account_id}", response_model=InternalAccountResponse)
def get_account_reference(
    account_id: int,
    _: InternalPrincipal,
    repository: AccountRepository = Depends(get_account_repository),
) -> InternalAccountResponse:
    return AccountService(repository).get_internal_account(account_id)
