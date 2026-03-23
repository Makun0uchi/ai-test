from datetime import datetime, timedelta

from fastapi import HTTPException, status
from libs.service_common.reference_validation import ReferenceValidator

from ..core.security import AuthContext
from ..models.timetable import Appointment, Timetable
from ..repositories.timetable_repository import TimetableRepository
from ..schemas.timetable import (
    AppointmentRequest,
    AppointmentResponse,
    TimetableRequest,
    TimetableResponse,
)

SLOT_SIZE = timedelta(minutes=30)
MAX_DURATION = timedelta(hours=12)


class TimetableService:
    def __init__(
        self,
        repository: TimetableRepository,
        reference_validator: ReferenceValidator,
    ) -> None:
        self.repository = repository
        self.reference_validator = reference_validator

    def create_timetable(self, payload: TimetableRequest) -> TimetableResponse:
        starts_at, ends_at = self._validate_interval(payload.starts_at, payload.ends_at)
        self._validate_references(
            hospital_id=payload.hospital_id,
            doctor_id=payload.doctor_id,
            room=payload.room,
        )
        self._ensure_no_overlap(
            hospital_id=payload.hospital_id,
            doctor_id=payload.doctor_id,
            room=payload.room,
            starts_at=starts_at,
            ends_at=ends_at,
        )
        timetable = self.repository.create_timetable(
            hospital_id=payload.hospital_id,
            doctor_id=payload.doctor_id,
            starts_at=starts_at,
            ends_at=ends_at,
            room=payload.room,
        )
        return self._to_timetable_response(timetable)

    def update_timetable(self, timetable_id: int, payload: TimetableRequest) -> TimetableResponse:
        timetable = self._require_timetable(timetable_id)
        starts_at, ends_at = self._validate_interval(payload.starts_at, payload.ends_at)
        self._validate_references(
            hospital_id=payload.hospital_id,
            doctor_id=payload.doctor_id,
            room=payload.room,
        )
        self._ensure_no_overlap(
            hospital_id=payload.hospital_id,
            doctor_id=payload.doctor_id,
            room=payload.room,
            starts_at=starts_at,
            ends_at=ends_at,
            exclude_id=timetable.id,
        )
        updated = self.repository.update_timetable(
            timetable,
            hospital_id=payload.hospital_id,
            doctor_id=payload.doctor_id,
            starts_at=starts_at,
            ends_at=ends_at,
            room=payload.room,
        )
        return self._to_timetable_response(updated)

    def delete_timetable(self, timetable_id: int) -> None:
        timetable = self._require_timetable(timetable_id)
        self.repository.delete_timetable(timetable)

    def delete_by_doctor(self, doctor_id: int) -> None:
        self.repository.delete_by_doctor(doctor_id)

    def delete_by_hospital(self, hospital_id: int) -> None:
        self.repository.delete_by_hospital(hospital_id)

    def list_by_hospital(
        self, hospital_id: int, start: datetime, end: datetime
    ) -> list[TimetableResponse]:
        self._validate_query_range(start, end)
        timetables = self.repository.list_by_hospital(hospital_id, start, end)
        return [self._to_timetable_response(item) for item in timetables]

    def list_by_doctor(
        self, doctor_id: int, start: datetime, end: datetime
    ) -> list[TimetableResponse]:
        self._validate_query_range(start, end)
        timetables = self.repository.list_by_doctor(doctor_id, start, end)
        return [self._to_timetable_response(item) for item in timetables]

    def list_by_hospital_room(
        self,
        hospital_id: int,
        room: str,
        start: datetime,
        end: datetime,
    ) -> list[TimetableResponse]:
        self._validate_query_range(start, end)
        timetables = self.repository.list_by_hospital_room(hospital_id, room, start, end)
        return [self._to_timetable_response(item) for item in timetables]

    def list_available_appointments(self, timetable_id: int) -> list[datetime]:
        timetable = self._require_timetable(timetable_id)
        booked = {
            appointment.time
            for appointment in self.repository.list_booked_appointments(timetable_id)
        }
        slots: list[datetime] = []
        current = timetable.starts_at
        while current < timetable.ends_at:
            if current not in booked:
                slots.append(current)
            current += SLOT_SIZE
        return slots

    def create_appointment(
        self,
        timetable_id: int,
        payload: AppointmentRequest,
        principal: AuthContext,
    ) -> AppointmentResponse:
        timetable = self._require_timetable(timetable_id)
        appointment_time = self._normalize_slot_time(payload.time)
        self._ensure_time_in_timetable(timetable, appointment_time)
        if self.repository.get_appointment_by_time(timetable_id, appointment_time) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Appointment slot is already booked"
            )
        appointment = self.repository.create_appointment(
            timetable_id=timetable_id,
            patient_id=principal.subject,
            time=appointment_time,
        )
        return self._to_appointment_response(appointment)

    def delete_appointment(self, appointment_id: int, principal: AuthContext) -> None:
        appointment = self.repository.get_appointment(appointment_id)
        if appointment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found"
            )
        elevated_roles = {"Admin", "Manager", "Doctor"}
        if (
            set(principal.roles).isdisjoint(elevated_roles)
            and appointment.patient_id != principal.subject
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        self.repository.delete_appointment(appointment)

    def _require_timetable(self, timetable_id: int) -> Timetable:
        timetable = self.repository.get_timetable(timetable_id)
        if timetable is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timetable not found")
        return timetable

    def _validate_interval(
        self, starts_at: datetime, ends_at: datetime
    ) -> tuple[datetime, datetime]:
        starts_at = self._normalize_slot_time(starts_at)
        ends_at = self._normalize_slot_time(ends_at)
        if ends_at <= starts_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The end of interval must be after start",
            )
        if ends_at - starts_at > MAX_DURATION:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Timetable interval must not exceed 12 hours",
            )
        return starts_at, ends_at

    def _validate_query_range(self, start: datetime, end: datetime) -> None:
        if end <= start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid query range"
            )

    def _normalize_slot_time(self, value: datetime) -> datetime:
        if value.minute not in {0, 30} or value.second != 0 or value.microsecond != 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Time must align to a 30-minute slot",
            )
        return value.replace(tzinfo=None)

    def _ensure_no_overlap(
        self,
        *,
        hospital_id: int,
        doctor_id: int,
        room: str,
        starts_at: datetime,
        ends_at: datetime,
        exclude_id: int | None = None,
    ) -> None:
        overlaps = self.repository.find_overlaps(
            hospital_id=hospital_id,
            doctor_id=doctor_id,
            room=room,
            starts_at=starts_at,
            ends_at=ends_at,
            exclude_id=exclude_id,
        )
        if overlaps:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Timetable overlaps with existing schedule",
            )

    def _ensure_time_in_timetable(self, timetable: Timetable, appointment_time: datetime) -> None:
        if appointment_time < timetable.starts_at or appointment_time >= timetable.ends_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Appointment time is outside timetable range",
            )

    def _validate_references(self, *, hospital_id: int, doctor_id: int, room: str) -> None:
        self.reference_validator.ensure_account_has_role(
            doctor_id,
            role="Doctor",
            missing_detail="Doctor account not found",
            wrong_role_detail="Referenced account is not a doctor",
        )
        self.reference_validator.ensure_hospital_exists(
            hospital_id,
            missing_detail="Hospital not found",
        )
        self.reference_validator.ensure_hospital_room_exists(
            hospital_id,
            room,
            missing_detail="Hospital room not found",
        )

    def _to_timetable_response(self, timetable: Timetable) -> TimetableResponse:
        return TimetableResponse(
            id=timetable.id,
            hospital_id=timetable.hospital_id,
            doctor_id=timetable.doctor_id,
            starts_at=timetable.starts_at,
            ends_at=timetable.ends_at,
            room=timetable.room,
        )

    def _to_appointment_response(self, appointment: Appointment) -> AppointmentResponse:
        return AppointmentResponse(
            id=appointment.id,
            timetable_id=appointment.timetable_id,
            patient_id=appointment.patient_id,
            time=appointment.time,
        )
