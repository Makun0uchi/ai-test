import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from libs.service_common.logging import configure_logging
from libs.service_common.migrations import run_database_migrations

from .core.config import Settings
from .core.database import DatabaseManager
from .events.dispatcher import HospitalOutboxDispatcher
from .events.publisher import (
    HospitalEventPublisher,
    InMemoryHospitalEventPublisher,
    RabbitMQHospitalEventPublisher,
)
from .routers.hospitals import router as hospitals_router
from .routers.internal import router as internal_router
from .routers.system import router as system_router

SERVICE_ROOT = Path(__file__).resolve().parents[1]


def create_hospital_event_publisher(settings: Settings) -> HospitalEventPublisher:
    if settings.rabbitmq_url.startswith("memory://"):
        return InMemoryHospitalEventPublisher()
    return RabbitMQHospitalEventPublisher(
        url=settings.rabbitmq_url,
        exchange_name=settings.hospital_events_exchange,
    )


def create_app(
    settings: Settings | None = None,
    hospital_event_publisher: HospitalEventPublisher | None = None,
) -> FastAPI:
    app_settings = settings or Settings()
    configure_logging(app_settings.service_name)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        run_database_migrations(
            alembic_ini_path=SERVICE_ROOT / "alembic.ini",
            database_url=app_settings.database_url,
        )
        database_manager = DatabaseManager(app_settings.database_url)
        app_hospital_event_publisher = hospital_event_publisher or create_hospital_event_publisher(
            app_settings
        )
        outbox_dispatcher = HospitalOutboxDispatcher(
            database_manager=database_manager,
            publisher=app_hospital_event_publisher,
            poll_interval_seconds=app_settings.outbox_poll_interval_seconds,
            batch_size=app_settings.outbox_batch_size,
        )
        outbox_task = asyncio.create_task(outbox_dispatcher.run_forever())

        app.state.settings = app_settings
        app.state.database_manager = database_manager
        app.state.hospital_event_publisher = app_hospital_event_publisher
        app.state.outbox_dispatcher = outbox_dispatcher

        yield
        outbox_dispatcher.stop()
        await outbox_task
        await app_hospital_event_publisher.close()
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
