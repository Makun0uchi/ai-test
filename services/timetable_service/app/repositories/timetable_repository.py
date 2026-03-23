from datetime import datetime

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session, joinedload

from ..models.timetable import Appointment, Timetable


class TimetableRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_timetable(
        self,
        *,
        hospital_id: int,
        doctor_id: int,
        starts_at: datetime,
        ends_at: datetime,
        room: str,
    ) -> Timetable:
        timetable = Timetable(
            hospital_id=hospital_id,
            doctor_id=doctor_id,
            starts_at=starts_at,
            ends_at=ends_at,
            room=room,
        )
        self.session.add(timetable)
        self.session.commit()
        self.session.refresh(timetable)
        return self.get_timetable(timetable.id) or timetable

    def get_timetable(self, timetable_id: int) -> Timetable | None:
        statement = (
            select(Timetable)
            .options(joinedload(Timetable.appointments))
            .where(Timetable.id == timetable_id)
        )
        return self.session.scalar(statement)

    def update_timetable(
        self,
        timetable: Timetable,
        *,
        hospital_id: int,
        doctor_id: int,
        starts_at: datetime,
        ends_at: datetime,
        room: str,
    ) -> Timetable:
        timetable.hospital_id = hospital_id
        timetable.doctor_id = doctor_id
        timetable.starts_at = starts_at
        timetable.ends_at = ends_at
        timetable.room = room
        self.session.add(timetable)
        self.session.commit()
        self.session.refresh(timetable)
        return self.get_timetable(timetable.id) or timetable

    def delete_timetable(self, timetable: Timetable) -> None:
        self.session.delete(timetable)
        self.session.commit()

    def delete_by_doctor(self, doctor_id: int) -> int:
        statement = delete(Timetable).where(Timetable.doctor_id == doctor_id)
        result = self.session.execute(statement)
        self.session.commit()
        return result.rowcount or 0

    def delete_by_hospital(self, hospital_id: int) -> int:
        statement = delete(Timetable).where(Timetable.hospital_id == hospital_id)
        result = self.session.execute(statement)
        self.session.commit()
        return result.rowcount or 0

    def list_by_hospital(self, hospital_id: int, start: datetime, end: datetime) -> list[Timetable]:
        statement = (
            select(Timetable)
            .where(
                Timetable.hospital_id == hospital_id,
                Timetable.starts_at < end,
                Timetable.ends_at > start,
            )
            .order_by(Timetable.starts_at)
        )
        return list(self.session.scalars(statement))

    def list_by_doctor(self, doctor_id: int, start: datetime, end: datetime) -> list[Timetable]:
        statement = (
            select(Timetable)
            .where(
                Timetable.doctor_id == doctor_id,
                Timetable.starts_at < end,
                Timetable.ends_at > start,
            )
            .order_by(Timetable.starts_at)
        )
        return list(self.session.scalars(statement))

    def list_by_hospital_room(
        self,
        hospital_id: int,
        room: str,
        start: datetime,
        end: datetime,
    ) -> list[Timetable]:
        statement = (
            select(Timetable)
            .where(
                Timetable.hospital_id == hospital_id,
                Timetable.room == room,
                Timetable.starts_at < end,
                Timetable.ends_at > start,
            )
            .order_by(Timetable.starts_at)
        )
        return list(self.session.scalars(statement))

    def find_overlaps(
        self,
        *,
        hospital_id: int,
        doctor_id: int,
        room: str,
        starts_at: datetime,
        ends_at: datetime,
        exclude_id: int | None = None,
    ) -> list[Timetable]:
        statement = select(Timetable).where(
            Timetable.starts_at < ends_at,
            Timetable.ends_at > starts_at,
            or_(
                Timetable.doctor_id == doctor_id,
                (Timetable.hospital_id == hospital_id) & (Timetable.room == room),
            ),
        )
        if exclude_id is not None:
            statement = statement.where(Timetable.id != exclude_id)
        return list(self.session.scalars(statement))

    def list_booked_appointments(self, timetable_id: int) -> list[Appointment]:
        statement = (
            select(Appointment)
            .where(Appointment.timetable_id == timetable_id)
            .order_by(Appointment.time)
        )
        return list(self.session.scalars(statement))

    def get_appointment(self, appointment_id: int) -> Appointment | None:
        statement = (
            select(Appointment)
            .options(joinedload(Appointment.timetable))
            .where(Appointment.id == appointment_id)
        )
        return self.session.scalar(statement)

    def get_appointment_by_time(self, timetable_id: int, time: datetime) -> Appointment | None:
        statement = select(Appointment).where(
            Appointment.timetable_id == timetable_id,
            Appointment.time == time,
        )
        return self.session.scalar(statement)

    def create_appointment(
        self, *, timetable_id: int, patient_id: int, time: datetime
    ) -> Appointment:
        appointment = Appointment(timetable_id=timetable_id, patient_id=patient_id, time=time)
        self.session.add(appointment)
        self.session.commit()
        self.session.refresh(appointment)
        return self.get_appointment(appointment.id) or appointment

    def delete_appointment(self, appointment: Appointment) -> None:
        self.session.delete(appointment)
        self.session.commit()
