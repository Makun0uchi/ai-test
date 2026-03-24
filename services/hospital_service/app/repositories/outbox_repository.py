from datetime import datetime

from libs.service_common.logging import get_correlation_id
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.outbox import HospitalOutbox


class HospitalOutboxRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_event(
        self,
        *,
        hospital_id: int,
        event_type: str,
        routing_key: str,
        payload: str,
    ) -> HospitalOutbox:
        event = HospitalOutbox(
            hospital_id=hospital_id,
            event_type=event_type,
            routing_key=routing_key,
            correlation_id=get_correlation_id(),
            payload=payload,
        )
        self.session.add(event)
        self.session.flush()
        return event

    def list_pending(self, limit: int) -> list[HospitalOutbox]:
        statement = (
            select(HospitalOutbox)
            .where(HospitalOutbox.published_at.is_(None))
            .order_by(HospitalOutbox.id)
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def mark_published(self, event: HospitalOutbox) -> None:
        event.published_at = datetime.utcnow()
        self.session.add(event)
        self.session.commit()
