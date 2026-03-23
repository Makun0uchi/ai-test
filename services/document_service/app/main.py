from contextlib import asynccontextmanager

from fastapi import FastAPI
from libs.service_common.logging import configure_logging
from libs.service_common.reference_validation import HttpReferenceValidator, ReferenceValidator

from .core.config import Settings
from .core.database import DatabaseManager
from .models import Base  # noqa: F401
from .repositories.history_repository import HistoryRepository
from .routers.history import router as history_router
from .routers.system import router as system_router
from .search.base import SearchGateway
from .search.elasticsearch_gateway import ElasticsearchSearchGateway
from .search.memory_gateway import InMemorySearchGateway


def create_search_gateway(settings: Settings) -> SearchGateway:
    if settings.elasticsearch_url.startswith("memory://"):
        return InMemorySearchGateway()
    return ElasticsearchSearchGateway(settings)


def create_reference_validator(settings: Settings) -> ReferenceValidator:
    return HttpReferenceValidator(
        account_service_url=settings.account_service_url,
        hospital_service_url=settings.hospital_service_url,
        internal_api_key=settings.internal_api_key,
    )


def sync_search_index(database_manager: DatabaseManager, search_gateway: SearchGateway) -> None:
    session = next(database_manager.get_session())
    try:
        repository = HistoryRepository(session)
        for history in repository.list_all():
            search_gateway.index_history(history)
    finally:
        session.close()


def create_app(
    settings: Settings | None = None,
    reference_validator: ReferenceValidator | None = None,
) -> FastAPI:
    app_settings = settings or Settings()
    configure_logging(app_settings.service_name)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database_manager = DatabaseManager(app_settings.database_url)
        database_manager.create_tables()
        search_gateway = create_search_gateway(app_settings)
        search_gateway.setup()
        app_reference_validator = reference_validator or create_reference_validator(app_settings)
        sync_search_index(database_manager, search_gateway)

        app.state.settings = app_settings
        app.state.database_manager = database_manager
        app.state.search_gateway = search_gateway
        app.state.reference_validator = app_reference_validator

        yield
        app_reference_validator.close()
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
    app.include_router(history_router)
    return app


app = create_app()
