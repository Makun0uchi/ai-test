from pydantic import BaseModel


class HealthResponse(BaseModel):
    service: str
    title: str
    version: str
    environment: str
    status: str
