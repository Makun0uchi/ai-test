from __future__ import annotations

import asyncio
from datetime import datetime

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
        history_payload = message.payload.get("history")
        if not isinstance(history_payload, dict):
            return

        history = HistoryRecord(
            id=int(history_payload["id"]),
            date=datetime.fromisoformat(str(history_payload["date"])),
            patient_id=int(history_payload["patientId"]),
            hospital_id=int(history_payload["hospitalId"]),
            doctor_id=int(history_payload["doctorId"]),
            room=str(history_payload["room"]),
            data=str(history_payload["data"]),
        )
        self.search_gateway.index_history(history)
