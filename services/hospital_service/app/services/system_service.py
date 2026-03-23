from ..core.config import Settings
from ..repositories.system_repository import SystemRepository
from ..schemas.system import HealthResponse


class SystemService:
    def __init__(self, repository: SystemRepository | None = None) -> None:
        self.repository = repository or SystemRepository()

    def get_health(self, settings: Settings) -> HealthResponse:
        status = self.repository.get_service_status(settings)
        return HealthResponse.model_validate(status, from_attributes=True)
