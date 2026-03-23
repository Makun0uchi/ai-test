from datetime import datetime

from pydantic import Field

from .common import CamelModel


class TimetableRequest(CamelModel):
    hospital_id: int = Field(alias="hospitalId", gt=0)
    doctor_id: int = Field(alias="doctorId", gt=0)
    starts_at: datetime = Field(alias="from")
    ends_at: datetime = Field(alias="to")
    room: str = Field(min_length=1, max_length=128)


class TimetableResponse(CamelModel):
    id: int
    hospital_id: int = Field(serialization_alias="hospitalId")
    doctor_id: int = Field(serialization_alias="doctorId")
    starts_at: datetime = Field(serialization_alias="from")
    ends_at: datetime = Field(serialization_alias="to")
    room: str


class AppointmentRequest(CamelModel):
    time: datetime


class AppointmentResponse(CamelModel):
    id: int
    timetable_id: int = Field(serialization_alias="timetableId")
    patient_id: int = Field(serialization_alias="patientId")
    time: datetime
