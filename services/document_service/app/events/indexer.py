from __future__ import annotations

import asyncio

from libs.contracts import HistoryChangedEvent

from ..models.history import HistoryRecord
from ..search.base import SearchGateway
from .publisher import HistoryEventMessage, HistoryEventSubscriber


class HistorySearchIndexer:
    def __init__(
        self,
        *,
        search_gateway: SearchGateway,
        subscriber: HistoryEventSubscriber,
    ) -> None:
        self.search_gateway = search_gateway
        self.subscriber = subscriber
        self._stop_event = asyncio.Event()

    async def prepare(self) -> None:
        await self.subscriber.prepare()

    async def run_forever(self) -> None:
        await self.subscriber.consume(handler=self._handle_message, stop_event=self._stop_event)

    def stop(self) -> None:
        self._stop_event.set()

    async def _handle_message(self, message: HistoryEventMessage) -> None:
        event = HistoryChangedEvent.model_validate(message.payload)
        history_payload = event.history

        history = HistoryRecord(
            id=history_payload.id,
            date=history_payload.date,
            patient_id=history_payload.patient_id,
            hospital_id=history_payload.hospital_id,
            doctor_id=history_payload.doctor_id,
            room=history_payload.room,
            data=history_payload.data,
        )
        self.search_gateway.index_history(history)
