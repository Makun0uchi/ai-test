from __future__ import annotations

import asyncio
import json

from ..core.database import DatabaseManager
from ..models.outbox import HistoryIndexOutbox
from ..repositories.outbox_repository import HistoryOutboxRepository
from .publisher import HistoryEventMessage, HistoryEventPublisher


class HistoryOutboxDispatcher:
    def __init__(
        self,
        *,
        database_manager: DatabaseManager,
        publisher: HistoryEventPublisher,
        poll_interval_seconds: float,
        batch_size: int,
    ) -> None:
        self.database_manager = database_manager
        self.publisher = publisher
        self.poll_interval_seconds = poll_interval_seconds
        self.batch_size = batch_size
        self._stop_event = asyncio.Event()

    async def run_forever(self) -> None:
        while not self._stop_event.is_set():
            await self.dispatch_pending()
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_interval_seconds)
            except TimeoutError:
                continue

    async def dispatch_pending(self) -> int:
        session = self.database_manager.session_factory()
        try:
            repository = HistoryOutboxRepository(session)
            pending_events = repository.list_pending(self.batch_size)
            published_count = 0
            for event in pending_events:
                await self.publisher.publish(self._to_message(event))
                repository.mark_published(event)
                published_count += 1
            return published_count
        finally:
            session.close()

    def stop(self) -> None:
        self._stop_event.set()

    def _to_message(self, event: HistoryIndexOutbox) -> HistoryEventMessage:
        return HistoryEventMessage(
            event_type=event.event_type,
            routing_key=event.routing_key,
            payload=json.loads(event.payload),
            correlation_id=event.correlation_id,
            aggregate_type="history",
            aggregate_id=event.history_id,
        )
