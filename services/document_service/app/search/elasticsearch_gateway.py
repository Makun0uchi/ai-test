from elasticsearch import Elasticsearch

from ..core.config import Settings
from ..models.history import HistoryRecord
from .base import SearchGateway, SearchQuery


class ElasticsearchSearchGateway(SearchGateway):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = Elasticsearch(settings.elasticsearch_url)
        self.index_name = settings.search_index_name

    def setup(self) -> None:
        if self.client.indices.exists(index=self.index_name):
            return
        self.client.indices.create(
            index=self.index_name,
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

    def index_history(self, history: HistoryRecord) -> None:
        self.client.index(
            index=self.index_name,
            id=str(history.id),
            document={
                "id": history.id,
                "date": history.date.isoformat(),
                "patient_id": history.patient_id,
                "doctor_id": history.doctor_id,
                "hospital_id": history.hospital_id,
                "room": history.room,
                "data": history.data,
            },
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
            index=self.index_name,
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
