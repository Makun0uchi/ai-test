from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from ..models.history import HistoryRecord


@dataclass(slots=True)
class SearchQuery:
    query: str | None = None
    patient_id: int | None = None
    doctor_id: int | None = None
    hospital_id: int | None = None
    room: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    page: int = 1
    size: int = 20


class SearchGateway(Protocol):
    def setup(self) -> None: ...

    def index_history(self, history: HistoryRecord) -> None: ...

    def search(self, query: SearchQuery) -> tuple[int, list[int]]: ...
