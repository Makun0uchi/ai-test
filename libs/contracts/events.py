import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


def dump_event_payload(event: BaseModel) -> str:
    return json.dumps(event.model_dump(by_alias=True, mode="json"), ensure_ascii=False)


class AccountSnapshot(ContractModel):
    id: int
    last_name: str = Field(alias="lastName")
    first_name: str = Field(alias="firstName")
    username: str
    roles: list[str]


class AccountChangedEvent(ContractModel):
    event_type: str = Field(alias="eventType")
    account_id: int = Field(alias="accountId")
    account: AccountSnapshot


class HospitalSnapshot(ContractModel):
    id: int
    name: str
    address: str
    contact_phone: str = Field(alias="contactPhone")
    rooms: list[str]


class HospitalChangedEvent(ContractModel):
    event_type: str = Field(alias="eventType")
    hospital_id: int = Field(alias="hospitalId")
    hospital: HospitalSnapshot


class TimetableAppointmentSnapshot(ContractModel):
    id: int
    patient_id: int = Field(alias="patientId")
    time: datetime


class TimetableSnapshot(ContractModel):
    id: int
    hospital_id: int = Field(alias="hospitalId")
    doctor_id: int = Field(alias="doctorId")
    starts_at: datetime = Field(alias="from")
    ends_at: datetime = Field(alias="to")
    room: str
    appointments: list[TimetableAppointmentSnapshot]


class TimetableChangedEvent(ContractModel):
    event_type: str = Field(alias="eventType")
    timetable_id: int = Field(alias="timetableId")
    timetable: TimetableSnapshot


class AppointmentSnapshot(ContractModel):
    id: int
    timetable_id: int = Field(alias="timetableId")
    patient_id: int = Field(alias="patientId")
    time: datetime


class AppointmentChangedEvent(ContractModel):
    event_type: str = Field(alias="eventType")
    appointment_id: int = Field(alias="appointmentId")
    appointment: AppointmentSnapshot


class HistorySnapshot(ContractModel):
    id: int
    date: datetime
    patient_id: int = Field(alias="patientId")
    hospital_id: int = Field(alias="hospitalId")
    doctor_id: int = Field(alias="doctorId")
    room: str
    data: str


class HistoryChangedEvent(ContractModel):
    event_type: str = Field(alias="eventType")
    history_id: int = Field(alias="historyId")
    history: HistorySnapshot
