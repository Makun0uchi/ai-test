from pydantic import Field

from .common import CamelModel


class InternalHospitalResponse(CamelModel):
    id: int
    name: str
    rooms: list[str]


class InternalHospitalRoomResponse(CamelModel):
    hospital_id: int = Field(serialization_alias="hospitalId")
    room: str
