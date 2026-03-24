from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from elasticsearch import Elasticsearch

from ..core.config import Settings
from ..models.history import HistoryRecord
from .base import SearchGateway, SearchQuery, SearchRebuildResult


class ElasticsearchSearchGateway(SearchGateway):
    def __init__(
        self,
        settings: Settings,
        *,
        client: Elasticsearch | None = None,
    ) -> None:
        self.settings = settings
        self.client = client or Elasticsearch(settings.elasticsearch_url)
        self.alias_name = settings.search_index_alias
        self.index_prefix = settings.search_index_prefix

    def setup(self) -> bool:
        if self.client.indices.exists_alias(name=self.alias_name):
            return False
        index_name = self._build_index_name()
        self._create_index(index_name)
        self.client.indices.put_alias(
            index=index_name,
            name=self.alias_name,
            is_write_index=True,
        )
        return True

    def index_history(self, history: HistoryRecord) -> None:
        self.client.index(
            index=self.alias_name,
            id=str(history.id),
            document=self._history_document(history),
            refresh="true",
        )

    def search(self, query: SearchQuery) -> tuple[int, list[int]]:
        filters: list[dict[str, object]] = []
        if query.patient_id is not None:
            filters.append({"term": {"patient_id": query.patient_id}})
        if query.doctor_id is not None:
            filters.append({"term": {"doctor_id": query.doctor_id}})
        if query.hospital_id is not None:
            filters.append({"term": {"hospital_id": query.hospital_id}})
        if query.room is not None:
            filters.append({"term": {"room": query.room}})
        if query.date_from is not None or query.date_to is not None:
            range_filter: dict[str, str] = {}
            if query.date_from is not None:
                range_filter["gte"] = query.date_from.isoformat()
            if query.date_to is not None:
                range_filter["lte"] = query.date_to.isoformat()
            filters.append({"range": {"date": range_filter}})

        must: list[dict[str, object]] = []
        if query.query:
            must.append({"match": {"data": {"query": query.query}}})

        response = self.client.search(
            index=self.alias_name,
            from_=(query.page - 1) * query.size,
            size=query.size,
            sort=[{"_score": "desc"}, {"date": "desc"}],
            query={"bool": {"must": must or [{"match_all": {}}], "filter": filters}},
        )
        hits = response["hits"]["hits"]
        total_info = response["hits"]["total"]
        total = total_info["value"] if isinstance(total_info, dict) else int(total_info)
        ids = [int(hit["_id"]) for hit in hits]
        return total, ids

    def rebuild(self, histories: list[HistoryRecord]) -> SearchRebuildResult:
        index_name = self._build_index_name()
        self._create_index(index_name)
        for history in histories:
            self.client.index(
                index=index_name,
                id=str(history.id),
                document=self._history_document(history),
            )
        self.client.indices.refresh(index=index_name)

        previous_indices = self._resolve_alias_indices()
        actions: list[dict[str, dict[str, Any]]] = [
            {
                "add": {
                    "index": index_name,
                    "alias": self.alias_name,
                    "is_write_index": True,
                }
            }
        ]
        for previous_index in previous_indices:
            actions.append(
                {
                    "remove": {
                        "index": previous_index,
                        "alias": self.alias_name,
                    }
                }
            )
        self.client.indices.update_aliases(actions=actions)
        return SearchRebuildResult(
            alias_name=self.alias_name,
            active_index_name=index_name,
            indexed_count=len(histories),
            strategy="elasticsearch_alias_full_rebuild",
            previous_indices=previous_indices,
        )

    def _resolve_alias_indices(self) -> list[str]:
        if not self.client.indices.exists_alias(name=self.alias_name):
            return []
        alias_mapping = self.client.indices.get_alias(name=self.alias_name)
        return list(alias_mapping.keys())

    def _build_index_name(self) -> str:
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        return f"{self.index_prefix}-{timestamp}"

    def _create_index(self, index_name: str) -> None:
        self.client.indices.create(
            index=index_name,
            settings={
                "analysis": {
                    "analyzer": {
                        "history_russian": {
                            "type": "russian",
                        }
                    }
                }
            },
            mappings={
                "properties": {
                    "id": {"type": "integer"},
                    "date": {"type": "date"},
                    "patient_id": {"type": "integer"},
                    "doctor_id": {"type": "integer"},
                    "hospital_id": {"type": "integer"},
                    "room": {"type": "keyword"},
                    "data": {"type": "text", "analyzer": "history_russian"},
                }
            },
        )

    def _history_document(self, history: HistoryRecord) -> dict[str, str | int]:
        return {
            "id": history.id,
            "date": history.date.isoformat(),
            "patient_id": history.patient_id,
            "doctor_id": history.doctor_id,
            "hospital_id": history.hospital_id,
            "room": history.room,
            "data": history.data,
        }
