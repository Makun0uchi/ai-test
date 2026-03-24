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


class HistorySearchReindexResponse(CamelModel):
    alias_name: str = Field(serialization_alias="aliasName")
    active_index_name: str = Field(serialization_alias="activeIndexName")
    indexed_count: int = Field(serialization_alias="indexedCount")
    strategy: str
    previous_indices: list[str] = Field(serialization_alias="previousIndices")
