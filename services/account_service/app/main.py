import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from libs.service_common.logging import CorrelationIdMiddleware, configure_logging
from libs.service_common.migrations import run_database_migrations
from libs.service_common.security import validate_security_settings

from .core.config import Settings
from .core.database import DatabaseManager
from .events.dispatcher import AccountOutboxDispatcher
from .events.publisher import (
    AccountEventPublisher,
    InMemoryAccountEventPublisher,
    RabbitMQAccountEventPublisher,
)
from .repositories.account_repository import AccountRepository
from .routers.accounts import router as accounts_router
from .routers.authentication import router as authentication_router
from .routers.doctors import router as doctors_router
from .routers.internal import router as internal_router
from .routers.system import router as system_router
from .services.account_service import AccountService

SERVICE_ROOT = Path(__file__).resolve().parents[1]


def create_account_event_publisher(settings: Settings) -> AccountEventPublisher:
    if settings.rabbitmq_url.startswith("memory://"):
        return InMemoryAccountEventPublisher()
    return RabbitMQAccountEventPublisher(
        url=settings.rabbitmq_url,
        exchange_name=settings.account_events_exchange,
    )


def create_app(
    settings: Settings | None = None,
    account_event_publisher: AccountEventPublisher | None = None,
) -> FastAPI:
    app_settings = settings or Settings()
    validate_security_settings(app_settings)
    configure_logging(
        app_settings.service_name,
        logstash_host=app_settings.logstash_host or None,
        logstash_port=app_settings.logstash_port,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        run_database_migrations(
            alembic_ini_path=SERVICE_ROOT / "alembic.ini",
            database_url=app_settings.database_url,
        )
        database_manager = DatabaseManager(app_settings.database_url)
        app_account_event_publisher = account_event_publisher or create_account_event_publisher(
            app_settings
        )

        session = database_manager.session_factory()
        try:
            AccountService(AccountRepository(session)).seed_defaults()
        finally:
            session.close()

        outbox_dispatcher = AccountOutboxDispatcher(
            database_manager=database_manager,
            publisher=app_account_event_publisher,
            poll_interval_seconds=app_settings.outbox_poll_interval_seconds,
            batch_size=app_settings.outbox_batch_size,
        )
        outbox_task = asyncio.create_task(outbox_dispatcher.run_forever())

        app.state.settings = app_settings
        app.state.database_manager = database_manager
        app.state.account_event_publisher = app_account_event_publisher
        app.state.outbox_dispatcher = outbox_dispatcher

        yield
        outbox_dispatcher.stop()
        await outbox_task
        await app_account_event_publisher.close()
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
    app.add_middleware(CorrelationIdMiddleware)
    app.include_router(system_router)
    app.include_router(authentication_router)
    app.include_router(accounts_router)
    app.include_router(doctors_router)
    app.include_router(internal_router)
    return app


app = create_app()
