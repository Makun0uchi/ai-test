from datetime import datetime

from pydantic import Field

from .common import CamelModel


class HistoryRequest(CamelModel):
    date: datetime
    patient_id: int = Field(alias="pacientId", gt=0)
    hospital_id: int = Field(alias="hospitalId", gt=0)
    doctor_id: int = Field(alias="doctorId", gt=0)
    room: str = Field(min_length=1, max_length=128)
    data: str = Field(min_length=1, max_length=4000)


class HistoryResponse(CamelModel):
    id: int
    date: datetime
    patient_id: int = Field(serialization_alias="pacientId")
    hospital_id: int = Field(serialization_alias="hospitalId")
    doctor_id: int = Field(serialization_alias="doctorId")
    room: str
    data: str


class HistorySearchResponse(CamelModel):
    total: int
    items: list[HistoryResponse]
