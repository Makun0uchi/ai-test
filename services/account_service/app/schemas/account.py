from pydantic import Field

from .common import CamelModel


class AccountResponse(CamelModel):
    id: int
    last_name: str = Field(serialization_alias="lastName")
    first_name: str = Field(serialization_alias="firstName")
    username: str
    roles: list[str]


class UpdateCurrentAccountRequest(CamelModel):
    last_name: str = Field(alias="lastName", min_length=1, max_length=128)
    first_name: str = Field(alias="firstName", min_length=1, max_length=128)
    password: str | None = Field(default=None, min_length=6, max_length=128)


class AdminCreateAccountRequest(CamelModel):
    last_name: str = Field(alias="lastName", min_length=1, max_length=128)
    first_name: str = Field(alias="firstName", min_length=1, max_length=128)
    username: str = Field(min_length=3, max_length=128)
    password: str = Field(min_length=6, max_length=128)
    roles: list[str] = Field(min_length=1)


class AdminUpdateAccountRequest(CamelModel):
    last_name: str = Field(alias="lastName", min_length=1, max_length=128)
    first_name: str = Field(alias="firstName", min_length=1, max_length=128)
    username: str = Field(min_length=3, max_length=128)
    password: str | None = Field(default=None, min_length=6, max_length=128)
    roles: list[str] = Field(min_length=1)
