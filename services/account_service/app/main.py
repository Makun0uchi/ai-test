from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from libs.service_common.logging import configure_logging
from libs.service_common.migrations import run_database_migrations

from .core.config import Settings
from .core.database import DatabaseManager
from .repositories.account_repository import AccountRepository
from .routers.accounts import router as accounts_router
from .routers.authentication import router as authentication_router
from .routers.doctors import router as doctors_router
from .routers.internal import router as internal_router
from .routers.system import router as system_router
from .services.account_service import AccountService

SERVICE_ROOT = Path(__file__).resolve().parents[1]


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()
    configure_logging(app_settings.service_name)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        run_database_migrations(
            alembic_ini_path=SERVICE_ROOT / "alembic.ini",
            database_url=app_settings.database_url,
        )
        database_manager = DatabaseManager(app_settings.database_url)

        app.state.settings = app_settings
        app.state.database_manager = database_manager

        session = database_manager.session_factory()
        try:
            AccountService(AccountRepository(session)).seed_defaults()
        finally:
            session.close()

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
    app.include_router(authentication_router)
    app.include_router(accounts_router)
    app.include_router(doctors_router)
    app.include_router(internal_router)
    return app


app = create_app()
