from fastapi import APIRouter, Depends, Query, Response, status

from ..core.config import Settings
from ..core.dependencies import get_account_repository, get_current_account, get_settings
from ..models.account import Account
from ..repositories.account_repository import AccountRepository
from ..schemas.auth import (
    RefreshTokenRequest,
    SignInRequest,
    SignUpRequest,
    TokenPairResponse,
    ValidateTokenResponse,
)
from ..services.auth_service import AuthService

router = APIRouter(prefix="/api/Authentication", tags=["authentication"])


@router.post("/SignUp", response_model=TokenPairResponse, status_code=status.HTTP_201_CREATED)
def sign_up(
    payload: SignUpRequest,
    settings: Settings = Depends(get_settings),
    repository: AccountRepository = Depends(get_account_repository),
) -> TokenPairResponse:
    return AuthService(repository).sign_up(payload, settings)


@router.post("/SignIn", response_model=TokenPairResponse)
def sign_in(
    payload: SignInRequest,
    settings: Settings = Depends(get_settings),
    repository: AccountRepository = Depends(get_account_repository),
) -> TokenPairResponse:
    return AuthService(repository).sign_in(payload, settings)


@router.put("/SignOut", status_code=status.HTTP_204_NO_CONTENT)
def sign_out(
    current_account: Account = Depends(get_current_account),
    repository: AccountRepository = Depends(get_account_repository),
) -> Response:
    AuthService(repository).sign_out(current_account.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/Validate", response_model=ValidateTokenResponse)
def validate(
    access_token: str = Query(alias="accessToken"),
    settings: Settings = Depends(get_settings),
    repository: AccountRepository = Depends(get_account_repository),
) -> ValidateTokenResponse:
    return AuthService(repository).validate(access_token, settings)


@router.post("/Refresh", response_model=TokenPairResponse)
def refresh(
    payload: RefreshTokenRequest,
    settings: Settings = Depends(get_settings),
    repository: AccountRepository = Depends(get_account_repository),
) -> TokenPairResponse:
    return AuthService(repository).refresh(payload, settings)
