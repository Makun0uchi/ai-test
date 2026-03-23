from fastapi import HTTPException, status

from ..core.config import Settings
from ..core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    refresh_token_expiry,
    verify_password,
)
from ..models.account import Account
from ..repositories.account_repository import AccountRepository
from ..schemas.auth import (
    RefreshTokenRequest,
    SignInRequest,
    SignUpRequest,
    TokenPairResponse,
    ValidateTokenResponse,
)


class AuthService:
    def __init__(self, repository: AccountRepository) -> None:
        self.repository = repository

    def sign_up(self, payload: SignUpRequest, settings: Settings) -> TokenPairResponse:
        if self.repository.get_account_by_username(payload.username) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Username already exists"
            )

        user_role = self.repository.get_or_create_role("User")
        account = self.repository.create_account(
            last_name=payload.last_name,
            first_name=payload.first_name,
            username=payload.username,
            password_hash=hash_password(payload.password),
            roles=[user_role],
        )
        return self._issue_tokens(account, settings)

    def sign_in(self, payload: SignInRequest, settings: Settings) -> TokenPairResponse:
        account = self.repository.get_account_by_username(payload.username)
        if account is None or not verify_password(payload.password, account.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )
        return self._issue_tokens(account, settings)

    def sign_out(self, account_id: int) -> None:
        self.repository.revoke_account_refresh_tokens(account_id)

    def validate(self, access_token: str, settings: Settings) -> ValidateTokenResponse:
        try:
            decode_access_token(access_token, settings)
        except HTTPException:
            return ValidateTokenResponse(is_valid=False)
        return ValidateTokenResponse(is_valid=True)

    def refresh(self, payload: RefreshTokenRequest, settings: Settings) -> TokenPairResponse:
        refresh_token = self.repository.get_active_refresh_token(payload.refresh_token)
        if refresh_token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

        self.repository.revoke_refresh_token(refresh_token)
        return self._issue_tokens(refresh_token.account, settings)

    def _issue_tokens(self, account: Account, settings: Settings) -> TokenPairResponse:
        roles = sorted(role.name for role in account.roles)
        access_token = create_access_token(
            subject=account.id,
            username=account.username,
            roles=roles,
            settings=settings,
        )
        refresh_token = generate_refresh_token()
        self.repository.create_refresh_token(
            token=refresh_token,
            account_id=account.id,
            expires_at=refresh_token_expiry(settings),
        )
        return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)
