from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.history import HistoryRecord


class HistoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

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
        date,
        patient_id: int,
        hospital_id: int,
        doctor_id: int,
        room: str,
        data: str,
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
        self.session.commit()
        self.session.refresh(history)
        return history

    def update_history(
        self,
        history: HistoryRecord,
        *,
        date,
        patient_id: int,
        hospital_id: int,
        doctor_id: int,
        room: str,
        data: str,
    ) -> HistoryRecord:
        history.date = date
        history.patient_id = patient_id
        history.hospital_id = hospital_id
        history.doctor_id = doctor_id
        history.room = room
        history.data = data
        self.session.add(history)
        self.session.commit()
        self.session.refresh(history)
        return history
