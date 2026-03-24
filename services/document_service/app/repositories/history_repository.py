from datetime import datetime

from libs.contracts import HistoryChangedEvent, HistorySnapshot, dump_event_payload
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.history import HistoryRecord
from ..repositories.outbox_repository import HistoryOutboxRepository


class HistoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.outbox_repository = HistoryOutboxRepository(session)

    def list_all(self) -> list[HistoryRecord]:
        statement = select(HistoryRecord).order_by(HistoryRecord.date.desc())
        return list(self.session.scalars(statement))

    def list_by_patient(self, patient_id: int) -> list[HistoryRecord]:
        statement = (
            select(HistoryRecord)
            .where(HistoryRecord.patient_id == patient_id)
            .order_by(HistoryRecord.date.desc())
        )
        return list(self.session.scalars(statement))

    def get_history(self, history_id: int) -> HistoryRecord | None:
        statement = select(HistoryRecord).where(HistoryRecord.id == history_id)
        return self.session.scalar(statement)

    def create_history(
        self,
        *,
        date: datetime,
        patient_id: int,
        hospital_id: int,
        doctor_id: int,
        room: str,
        data: str,
        event_type: str,
        routing_key: str,
    ) -> HistoryRecord:
        history = HistoryRecord(
            date=date,
            patient_id=patient_id,
            hospital_id=hospital_id,
            doctor_id=doctor_id,
            room=room,
            data=data,
        )
        self.session.add(history)
        self.session.flush()
        self.outbox_repository.create_event(
            history_id=history.id,
            event_type=event_type,
            routing_key=routing_key,
            payload=self._serialize_payload(history, event_type),
        )
        self.session.commit()
        self.session.refresh(history)
        return history

    def update_history(
        self,
        history: HistoryRecord,
        *,
        date: datetime,
        patient_id: int,
        hospital_id: int,
        doctor_id: int,
        room: str,
        data: str,
        event_type: str,
        routing_key: str,
    ) -> HistoryRecord:
        history.date = date
        history.patient_id = patient_id
        history.hospital_id = hospital_id
        history.doctor_id = doctor_id
        history.room = room
        history.data = data
        self.session.add(history)
        self.session.flush()
        self.outbox_repository.create_event(
            history_id=history.id,
            event_type=event_type,
            routing_key=routing_key,
            payload=self._serialize_payload(history, event_type),
        )
        self.session.commit()
        self.session.refresh(history)
        return history

    def _serialize_payload(self, history: HistoryRecord, event_type: str) -> str:
        event = HistoryChangedEvent(
            eventType=event_type,
            historyId=history.id,
            history=HistorySnapshot(
                id=history.id,
                date=history.date,
                patientId=history.patient_id,
                hospitalId=history.hospital_id,
                doctorId=history.doctor_id,
                room=history.room,
                data=history.data,
            ),
        )
        return dump_event_payload(event)
