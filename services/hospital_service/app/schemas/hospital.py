from pydantic import Field

from .common import CamelModel


class HospitalRequest(CamelModel):
    name: str = Field(min_length=1, max_length=255)
    address: str = Field(min_length=1, max_length=512)
    contact_phone: str = Field(alias="contactPhone", min_length=1, max_length=64)
    rooms: list[str] = Field(min_length=1)


class HospitalResponse(CamelModel):
    id: int
    name: str
    address: str
    contact_phone: str = Field(serialization_alias="contactPhone")
    rooms: list[str]
