from pydantic import Field

from .common import CamelModel


class SignUpRequest(CamelModel):
    last_name: str = Field(alias="lastName", min_length=1, max_length=128)
    first_name: str = Field(alias="firstName", min_length=1, max_length=128)
    username: str = Field(min_length=3, max_length=128)
    password: str = Field(min_length=6, max_length=128)


class SignInRequest(CamelModel):
    username: str
    password: str


class RefreshTokenRequest(CamelModel):
    refresh_token: str = Field(alias="refreshToken")


class TokenPairResponse(CamelModel):
    access_token: str = Field(serialization_alias="accessToken")
    refresh_token: str = Field(serialization_alias="refreshToken")


class ValidateTokenResponse(CamelModel):
    is_valid: bool = Field(serialization_alias="isValid")
