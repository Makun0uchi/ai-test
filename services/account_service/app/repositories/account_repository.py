import json
from datetime import datetime

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, joinedload

from ..models.account import Account, RefreshToken, Role
from .outbox_repository import AccountOutboxRepository


class AccountRepository:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.outbox_repository = AccountOutboxRepository(session)

    def get_account_by_id(self, account_id: int) -> Account | None:
        statement = (
            select(Account).options(joinedload(Account.roles)).where(Account.id == account_id)
        )
        return self.session.scalar(statement)

    def get_account_by_username(self, username: str) -> Account | None:
        statement = (
            select(Account).options(joinedload(Account.roles)).where(Account.username == username)
        )
        return self.session.scalar(statement)

    def list_accounts(self, offset: int, limit: int) -> list[Account]:
        statement = (
            select(Account)
            .options(joinedload(Account.roles))
            .order_by(Account.id)
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(statement).unique())

    def create_account(
        self,
        *,
        last_name: str,
        first_name: str,
        username: str,
        password_hash: str,
        roles: list[Role],
        event_type: str | None = None,
        routing_key: str | None = None,
    ) -> Account:
        account = Account(
            last_name=last_name,
            first_name=first_name,
            username=username,
            password_hash=password_hash,
            roles=roles,
        )
        self.session.add(account)
        self.session.flush()
        if event_type is not None and routing_key is not None:
            self.outbox_repository.create_event(
                account_id=account.id,
                event_type=event_type,
                routing_key=routing_key,
                payload=self._serialize_account_payload(account, event_type),
            )
        self.session.commit()
        self.session.refresh(account)
        return self.get_account_by_id(account.id) or account

    def update_account(
        self,
        account: Account,
        *,
        last_name: str,
        first_name: str,
        username: str | None = None,
        password_hash: str | None = None,
        roles: list[Role] | None = None,
        event_type: str | None = None,
        routing_key: str | None = None,
    ) -> Account:
        account.last_name = last_name
        account.first_name = first_name
        if username is not None:
            account.username = username
        if password_hash is not None:
            account.password_hash = password_hash
        if roles is not None:
            account.roles = roles
        self.session.add(account)
        self.session.flush()
        if event_type is not None and routing_key is not None:
            self.outbox_repository.create_event(
                account_id=account.id,
                event_type=event_type,
                routing_key=routing_key,
                payload=self._serialize_account_payload(account, event_type),
            )
        self.session.commit()
        self.session.refresh(account)
        return self.get_account_by_id(account.id) or account

    def delete_account(
        self,
        account: Account,
        *,
        event_type: str | None = None,
        routing_key: str | None = None,
    ) -> None:
        if event_type is not None and routing_key is not None:
            self.outbox_repository.create_event(
                account_id=account.id,
                event_type=event_type,
                routing_key=routing_key,
                payload=self._serialize_account_payload(account, event_type),
            )
        self.session.delete(account)
        self.session.commit()

    def get_or_create_role(self, name: str) -> Role:
        role = self.session.scalar(select(Role).where(Role.name == name))
        if role is None:
            role = Role(name=name)
            self.session.add(role)
            self.session.commit()
            self.session.refresh(role)
        return role

    def get_roles(self, names: list[str]) -> list[Role]:
        if not names:
            return []
        statement = select(Role).where(Role.name.in_(names)).order_by(Role.name)
        return list(self.session.scalars(statement))

    def list_doctors(self, *, name_filter: str | None, offset: int, limit: int) -> list[Account]:
        statement = (
            select(Account)
            .join(Account.roles)
            .options(joinedload(Account.roles))
            .where(Role.name == "Doctor")
            .order_by(Account.id)
            .offset(offset)
            .limit(limit)
        )
        if name_filter:
            pattern = f"%{name_filter.lower()}%"
            statement = statement.where(
                or_(
                    func.lower(Account.first_name).like(pattern),
                    func.lower(Account.last_name).like(pattern),
                    func.lower(Account.first_name + " " + Account.last_name).like(pattern),
                    func.lower(Account.last_name + " " + Account.first_name).like(pattern),
                )
            )
        return list(self.session.scalars(statement).unique())

    def create_refresh_token(
        self, *, token: str, account_id: int, expires_at: datetime
    ) -> RefreshToken:
        refresh_token = RefreshToken(token=token, account_id=account_id, expires_at=expires_at)
        self.session.add(refresh_token)
        self.session.commit()
        self.session.refresh(refresh_token)
        return refresh_token

    def get_active_refresh_token(self, token: str) -> RefreshToken | None:
        statement = (
            select(RefreshToken)
            .options(joinedload(RefreshToken.account).joinedload(Account.roles))
            .where(RefreshToken.token == token)
        )
        refresh_token = self.session.scalar(statement)
        if refresh_token is None:
            return None
        if refresh_token.revoked_at is not None:
            return None
        if refresh_token.expires_at <= datetime.utcnow():
            return None
        return refresh_token

    def revoke_refresh_token(self, refresh_token: RefreshToken) -> None:
        refresh_token.revoked_at = datetime.utcnow()
        self.session.add(refresh_token)
        self.session.commit()

    def revoke_account_refresh_tokens(self, account_id: int) -> None:
        statement = select(RefreshToken).where(
            RefreshToken.account_id == account_id,
            RefreshToken.revoked_at.is_(None),
        )
        tokens = list(self.session.scalars(statement))
        for token in tokens:
            token.revoked_at = datetime.utcnow()
            self.session.add(token)
        self.session.commit()

    def ensure_roles(self, role_names: list[str]) -> list[Role]:
        return [self.get_or_create_role(name) for name in role_names]

    def delete_all(self) -> None:
        self.session.execute(delete(RefreshToken))
        self.session.execute(delete(Account))
        self.session.execute(delete(Role))
        self.session.commit()

    def _serialize_account_payload(self, account: Account, event_type: str) -> str:
        payload = {
            "eventType": event_type,
            "accountId": account.id,
            "account": {
                "id": account.id,
                "lastName": account.last_name,
                "firstName": account.first_name,
                "username": account.username,
                "roles": sorted(role.name for role in account.roles),
            },
        }
        return json.dumps(payload, ensure_ascii=False)
