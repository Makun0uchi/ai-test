from ..models.history import HistoryRecord
from .base import SearchGateway, SearchQuery, SearchRebuildResult


class InMemorySearchGateway(SearchGateway):
    def __init__(self, *, alias_name: str = "memory-history") -> None:
        self.alias_name = alias_name
        self._documents: dict[int, HistoryRecord] = {}

    def setup(self) -> bool:
        return True

    def index_history(self, history: HistoryRecord) -> None:
        self._documents[history.id] = history

    def search(self, query: SearchQuery) -> tuple[int, list[int]]:
        items = list(self._documents.values())
        filtered = [item for item in items if self._matches(item, query)]
        filtered.sort(key=lambda item: item.date, reverse=True)
        start = max(query.page - 1, 0) * query.size
        end = start + query.size
        return len(filtered), [item.id for item in filtered[start:end]]

    def rebuild(self, histories: list[HistoryRecord]) -> SearchRebuildResult:
        self._documents.clear()
        for history in histories:
            self.index_history(history)
        return SearchRebuildResult(
            alias_name=self.alias_name,
            active_index_name="in-memory",
            indexed_count=len(histories),
            strategy="in_memory_full_rebuild",
            previous_indices=[],
        )

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
