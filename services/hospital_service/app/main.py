from contextlib import asynccontextmanager

from fastapi import FastAPI
from libs.service_common.logging import configure_logging

from .core.config import Settings
from .core.database import DatabaseManager
from .models import Base  # noqa: F401
from .routers.hospitals import router as hospitals_router
from .routers.internal import router as internal_router
from .routers.system import router as system_router


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()
    configure_logging(app_settings.service_name)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database_manager = DatabaseManager(app_settings.database_url)
        database_manager.create_tables()

        app.state.settings = app_settings
        app.state.database_manager = database_manager

        yield
        database_manager.dispose()

    app = FastAPI(
        title=app_settings.service_title,
        description=app_settings.service_description,
        version=app_settings.service_version,
        docs_url=app_settings.docs_url,
        openapi_url=app_settings.openapi_url,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.include_router(system_router)
    app.include_router(hospitals_router)
    app.include_router(internal_router)
    return app


app = create_app()
