from fastapi import HTTPException, status

from ..core.security import AuthContext
from ..repositories.history_repository import HistoryRepository
from ..schemas.history import HistorySearchReindexResponse
from ..search.base import SearchGateway


class SearchMaintenanceService:
    def __init__(
        self,
        repository: HistoryRepository,
        search_gateway: SearchGateway,
    ) -> None:
        self.repository = repository
        self.search_gateway = search_gateway

    def rebuild_index(self, principal: AuthContext) -> HistorySearchReindexResponse:
        if set(principal.roles).isdisjoint({"Admin", "Manager"}):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        result = self.search_gateway.rebuild(self.repository.list_all())
        return HistorySearchReindexResponse(
            alias_name=result.alias_name,
            active_index_name=result.active_index_name,
            indexed_count=result.indexed_count,
            strategy=result.strategy,
            previous_indices=result.previous_indices,
        )
