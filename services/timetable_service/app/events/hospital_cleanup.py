from libs.contracts import HospitalChangedEvent
from libs.service_common.messaging import (
    BackgroundEventConsumer,
    EventMessage,
    EventSubscriber,
    parse_event_payload,
)

from ..core.database import DatabaseManager
from ..repositories.timetable_repository import TimetableRepository
from ..services.timetable_service import TimetableService


class HospitalDeletedTimetableCleanupConsumer:
    def __init__(
        self,
        *,
        database_manager: DatabaseManager,
        subscriber: EventSubscriber,
    ) -> None:
        self.database_manager = database_manager
        self.subscriber = subscriber
        self._consumer = BackgroundEventConsumer(
            name="timetable-hospital-cleanup",
            subscriber=subscriber,
            handler=self._handle_message,
        )

    async def prepare(self) -> None:
        await self._consumer.prepare()

    async def run_forever(self) -> None:
        await self._consumer.run_forever()

    def stop(self) -> None:
        self._consumer.stop()

    async def _handle_message(self, message: EventMessage) -> None:
        event = parse_event_payload(message, HospitalChangedEvent)
        session = next(self.database_manager.get_session())
        try:
            repository = TimetableRepository(session)
            repository.delete_by_hospital(
                event.hospital_id,
                event_type=TimetableService.TIMETABLE_DELETED_EVENT_TYPE,
                routing_key=TimetableService.TIMETABLE_DELETED_EVENT_TYPE,
            )
        finally:
            session.close()
