from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.outbox import AccountOutbox


class AccountOutboxRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_event(
        self,
        *,
        account_id: int,
        event_type: str,
        routing_key: str,
        payload: str,
    ) -> AccountOutbox:
        event = AccountOutbox(
            account_id=account_id,
            event_type=event_type,
            routing_key=routing_key,
            payload=payload,
        )
        self.session.add(event)
        self.session.flush()
        return event

    def list_pending(self, limit: int) -> list[AccountOutbox]:
        statement = (
            select(AccountOutbox)
            .where(AccountOutbox.published_at.is_(None))
            .order_by(AccountOutbox.id)
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def mark_published(self, event: AccountOutbox) -> None:
        event.published_at = datetime.utcnow()
        self.session.add(event)
        self.session.commit()
