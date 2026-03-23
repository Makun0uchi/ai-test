from fastapi import FastAPI
from libs.service_common.logging import configure_logging

from .core.config import get_settings
from .routers.system import router as system_router

settings = get_settings()
configure_logging(settings.service_name)

app = FastAPI(
    title=settings.service_title,
    description=settings.service_description,
    version=settings.service_version,
    docs_url=settings.docs_url,
    openapi_url=settings.openapi_url,
    redoc_url=None,
)
app.include_router(system_router)
