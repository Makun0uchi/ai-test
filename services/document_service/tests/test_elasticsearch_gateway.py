from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any, cast

from services.document_service.app.core.config import Settings
from services.document_service.app.models.history import HistoryRecord
from services.document_service.app.search.elasticsearch_gateway import ElasticsearchSearchGateway


class FakeIndicesClient:
    def __init__(self) -> None:
        self.created_indices: list[str] = []
        self.aliases: dict[str, list[str]] = {}
        self.refreshed_indices: list[str] = []

    def exists_alias(self, *, name: str) -> bool:
        return name in self.aliases and len(self.aliases[name]) > 0

    def create(self, *, index: str, settings: dict[str, Any], mappings: dict[str, Any]) -> None:
        self.created_indices.append(index)

    def put_alias(self, *, index: str, name: str, is_write_index: bool = False) -> None:
        self.aliases[name] = [index]

    def get_alias(self, *, name: str) -> dict[str, dict[str, Any]]:
        return {index_name: {} for index_name in self.aliases.get(name, [])}

    def update_aliases(self, *, actions: Sequence[dict[str, dict[str, Any]]]) -> None:
        for action in actions:
            if "remove" in action:
                alias_name = cast(str, action["remove"]["alias"])
                index_name = cast(str, action["remove"]["index"])
                self.aliases[alias_name] = [
                    existing
                    for existing in self.aliases.get(alias_name, [])
                    if existing != index_name
                ]
            if "add" in action:
                alias_name = cast(str, action["add"]["alias"])
                index_name = cast(str, action["add"]["index"])
                self.aliases[alias_name] = [index_name]

    def refresh(self, *, index: str) -> None:
        self.refreshed_indices.append(index)


class FakeElasticsearchClient:
    def __init__(self) -> None:
        self.indices = FakeIndicesClient()
        self.indexed_documents: dict[str, dict[str, dict[str, Any]]] = {}

    def index(
        self,
        *,
        index: str,
        id: str,
        document: dict[str, Any],
        refresh: str | None = None,
    ) -> None:
        if index not in self.indexed_documents:
            self.indexed_documents[index] = {}
        self.indexed_documents[index][id] = document


def _settings() -> Settings:
    return Settings(
        DATABASE_URL="sqlite+pysqlite:///ignored.db",
        ELASTICSEARCH_URL="http://example.invalid:9200",
        SEARCH_INDEX_ALIAS="history-records",
        SEARCH_INDEX_PREFIX="history-records-v1",
    )


def _history(history_id: int) -> HistoryRecord:
    return HistoryRecord(
        id=history_id,
        date=datetime(2026, 3, 24, 19, 0, 0),
        patient_id=10 + history_id,
        hospital_id=2,
        doctor_id=7,
        room="201",
        data=f"history-{history_id}",
    )


def test_setup_creates_alias_backed_index() -> None:
    fake_client = FakeElasticsearchClient()
    gateway = ElasticsearchSearchGateway(_settings(), client=cast(Any, fake_client))

    needs_rebuild = gateway.setup()

    assert needs_rebuild is True
    assert len(fake_client.indices.created_indices) == 1
    assert fake_client.indices.aliases[gateway.alias_name] == [
        fake_client.indices.created_indices[0]
    ]


def test_rebuild_switches_alias_to_new_index() -> None:
    fake_client = FakeElasticsearchClient()
    fake_client.indices.aliases["history-records"] = ["history-records-v1-old"]
    gateway = ElasticsearchSearchGateway(_settings(), client=cast(Any, fake_client))

    result = gateway.rebuild([_history(1), _history(2)])

    assert result.alias_name == "history-records"
    assert result.previous_indices == ["history-records-v1-old"]
    assert result.active_index_name.startswith("history-records-v1-")
    assert fake_client.indices.aliases["history-records"] == [result.active_index_name]
    assert fake_client.indices.refreshed_indices == [result.active_index_name]
    assert set(fake_client.indexed_documents[result.active_index_name].keys()) == {"1", "2"}
