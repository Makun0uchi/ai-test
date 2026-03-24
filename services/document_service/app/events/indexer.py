from __future__ import annotations

from libs.contracts import HistoryChangedEvent
from libs.service_common.messaging import BackgroundEventConsumer, parse_event_payload

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
        self._consumer = BackgroundEventConsumer(
            name="document-history-indexer",
            subscriber=subscriber,
            handler=self._handle_message,
        )

    async def prepare(self) -> None:
        await self._consumer.prepare()

    async def run_forever(self) -> None:
        await self._consumer.run_forever()

    def stop(self) -> None:
        self._consumer.stop()

    async def _handle_message(self, message: HistoryEventMessage) -> None:
        event = parse_event_payload(message, HistoryChangedEvent)
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
