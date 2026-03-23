from fastapi import APIRouter, Depends

from ..core.config import Settings
from ..core.dependencies import get_settings
from ..schemas.system import HealthResponse
from ..services.system_service import SystemService

router = APIRouter(tags=["system"])
service = SystemService()


@router.get("/health", response_model=HealthResponse, summary="Service health")
def read_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return service.get_health(settings)
