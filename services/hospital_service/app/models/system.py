from dataclasses import dataclass


@dataclass(slots=True)
class ServiceStatus:
    service: str
    title: str
    version: str
    environment: str
    status: str = "ok"
