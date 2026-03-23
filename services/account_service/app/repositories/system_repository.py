from ..core.config import Settings
from ..models.system import ServiceStatus


class SystemRepository:
    def get_service_status(self, settings: Settings) -> ServiceStatus:
        return ServiceStatus(
            service=settings.service_name,
            title=settings.service_title,
            version=settings.service_version,
            environment=settings.service_env,
        )
