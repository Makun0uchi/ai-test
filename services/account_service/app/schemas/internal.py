from .common import CamelModel


class InternalAccountResponse(CamelModel):
    id: int
    username: str
    roles: list[str]
