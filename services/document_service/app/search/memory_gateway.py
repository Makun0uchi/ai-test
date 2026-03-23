from ..models.history import HistoryRecord
from .base import SearchGateway, SearchQuery


class InMemorySearchGateway(SearchGateway):
    def __init__(self) -> None:
        self._documents: dict[int, HistoryRecord] = {}

    def setup(self) -> None:
        return None

    def index_history(self, history: HistoryRecord) -> None:
        self._documents[history.id] = history

    def search(self, query: SearchQuery) -> tuple[int, list[int]]:
        items = list(self._documents.values())
        filtered = [item for item in items if self._matches(item, query)]
        filtered.sort(key=lambda item: item.date, reverse=True)
        start = max(query.page - 1, 0) * query.size
        end = start + query.size
        return len(filtered), [item.id for item in filtered[start:end]]

    def _matches(self, history: HistoryRecord, query: SearchQuery) -> bool:
        if query.patient_id is not None and history.patient_id != query.patient_id:
            return False
        if query.doctor_id is not None and history.doctor_id != query.doctor_id:
            return False
        if query.hospital_id is not None and history.hospital_id != query.hospital_id:
            return False
        if query.room is not None and history.room != query.room:
            return False
        if query.date_from is not None and history.date < query.date_from:
            return False
        if query.date_to is not None and history.date > query.date_to:
            return False
        if query.query:
            haystack = " ".join([history.data, history.room]).lower()
            needles = [part for part in query.query.lower().split() if part]
            return all(needle in haystack for needle in needles)
        return True
