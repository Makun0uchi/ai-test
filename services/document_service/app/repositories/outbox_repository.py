from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.outbox import HistoryIndexOutbox


class HistoryOutboxRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_event(
        self,
        *,
        history_id: int,
        event_type: str,
        routing_key: str,
        payload: str,
    ) -> HistoryIndexOutbox:
        event = HistoryIndexOutbox(
            history_id=history_id,
            event_type=event_type,
            routing_key=routing_key,
            payload=payload,
        )
        self.session.add(event)
        self.session.flush()
        return event

    def list_pending(self, limit: int) -> list[HistoryIndexOutbox]:
        statement = (
            select(HistoryIndexOutbox)
            .where(HistoryIndexOutbox.published_at.is_(None))
            .order_by(HistoryIndexOutbox.id)
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def mark_published(self, event: HistoryIndexOutbox) -> None:
        event.published_at = datetime.utcnow()
        self.session.add(event)
        self.session.commit()
