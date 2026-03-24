from fastapi import HTTPException, status

from ..core.security import hash_password
from ..models.account import Account
from ..repositories.account_repository import AccountRepository
from ..schemas.account import (
    AccountResponse,
    AdminCreateAccountRequest,
    AdminUpdateAccountRequest,
    UpdateCurrentAccountRequest,
)
from ..schemas.internal import InternalAccountResponse


class AccountService:
    CREATED_EVENT_TYPE = "account.created.v1"
    UPDATED_EVENT_TYPE = "account.updated.v1"
    DELETED_EVENT_TYPE = "account.deleted.v1"

    def __init__(self, repository: AccountRepository) -> None:
        self.repository = repository

    def get_me(self, account: Account) -> AccountResponse:
        return self._to_response(account)

    def update_me(self, account: Account, payload: UpdateCurrentAccountRequest) -> AccountResponse:
        password_hash = hash_password(payload.password) if payload.password else None
        updated = self.repository.update_account(
            account,
            last_name=payload.last_name,
            first_name=payload.first_name,
            password_hash=password_hash,
            event_type=self.UPDATED_EVENT_TYPE,
            routing_key=self.UPDATED_EVENT_TYPE,
        )
        return self._to_response(updated)

    def list_accounts(self, offset: int, limit: int) -> list[AccountResponse]:
        return [
            self._to_response(account) for account in self.repository.list_accounts(offset, limit)
        ]

    def get_internal_account(self, account_id: int) -> InternalAccountResponse:
        account = self._require_account(account_id)
        return InternalAccountResponse(
            id=account.id,
            username=account.username,
            roles=sorted(role.name for role in account.roles),
        )

    def create_account(self, payload: AdminCreateAccountRequest) -> AccountResponse:
        if self.repository.get_account_by_username(payload.username) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Username already exists"
            )

        roles = self.repository.ensure_roles(payload.roles)
        account = self.repository.create_account(
            last_name=payload.last_name,
            first_name=payload.first_name,
            username=payload.username,
            password_hash=hash_password(payload.password),
            roles=roles,
            event_type=self.CREATED_EVENT_TYPE,
            routing_key=self.CREATED_EVENT_TYPE,
        )
        return self._to_response(account)

    def update_account(
        self, account_id: int, payload: AdminUpdateAccountRequest
    ) -> AccountResponse:
        account = self._require_account(account_id)

        existing_account = self.repository.get_account_by_username(payload.username)
        if existing_account is not None and existing_account.id != account_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Username already exists"
            )

        password_hash = hash_password(payload.password) if payload.password else None
        roles = self.repository.ensure_roles(payload.roles)
        updated = self.repository.update_account(
            account,
            last_name=payload.last_name,
            first_name=payload.first_name,
            username=payload.username,
            password_hash=password_hash,
            roles=roles,
            event_type=self.UPDATED_EVENT_TYPE,
            routing_key=self.UPDATED_EVENT_TYPE,
        )
        return self._to_response(updated)

    def delete_account(self, account_id: int) -> None:
        account = self._require_account(account_id)
        self.repository.delete_account(
            account,
            event_type=self.DELETED_EVENT_TYPE,
            routing_key=self.DELETED_EVENT_TYPE,
        )

    def seed_defaults(self) -> None:
        default_accounts = [
            ("admin", "Admin", "Admin", ["Admin"]),
            ("manager", "Manager", "Manager", ["Manager"]),
            ("doctor", "Doctor", "Doctor", ["Doctor"]),
            ("user", "User", "User", ["User"]),
        ]
        for username, last_name, first_name, roles in default_accounts:
            if self.repository.get_account_by_username(username) is not None:
                continue
            self.repository.create_account(
                last_name=last_name,
                first_name=first_name,
                username=username,
                password_hash=hash_password(username),
                roles=self.repository.ensure_roles(roles),
            )

    def _to_response(self, account: Account) -> AccountResponse:
        return AccountResponse(
            id=account.id,
            last_name=account.last_name,
            first_name=account.first_name,
            username=account.username,
            roles=sorted(role.name for role in account.roles),
        )

    def _require_account(self, account_id: int) -> Account:
        account = self.repository.get_account_by_id(account_id)
        if account is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
        return account
