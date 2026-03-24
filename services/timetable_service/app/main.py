import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from libs.service_common.logging import configure_logging
from libs.service_common.migrations import run_database_migrations
from libs.service_common.reference_validation import HttpReferenceValidator, ReferenceValidator

from .core.config import Settings
from .core.database import DatabaseManager
from .events.dispatcher import TimetableOutboxDispatcher
from .events.publisher import (
    InMemoryTimetableEventPublisher,
    RabbitMQTimetableEventPublisher,
    TimetableEventPublisher,
)
from .routers.appointment import router as appointment_router
from .routers.system import router as system_router
from .routers.timetable import router as timetable_router

SERVICE_ROOT = Path(__file__).resolve().parents[1]


def create_reference_validator(settings: Settings) -> ReferenceValidator:
    return HttpReferenceValidator(
        account_service_url=settings.account_service_url,
        hospital_service_url=settings.hospital_service_url,
        internal_api_key=settings.internal_api_key,
    )


def create_timetable_event_publisher(settings: Settings) -> TimetableEventPublisher:
    if settings.rabbitmq_url.startswith("memory://"):
        return InMemoryTimetableEventPublisher()
    return RabbitMQTimetableEventPublisher(
        url=settings.rabbitmq_url,
        exchange_name=settings.timetable_events_exchange,
    )


def create_app(
    settings: Settings | None = None,
    reference_validator: ReferenceValidator | None = None,
    timetable_event_publisher: TimetableEventPublisher | None = None,
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
        app_reference_validator = reference_validator or create_reference_validator(app_settings)
        app_timetable_event_publisher = (
            timetable_event_publisher or create_timetable_event_publisher(app_settings)
        )
        outbox_dispatcher = TimetableOutboxDispatcher(
            database_manager=database_manager,
            publisher=app_timetable_event_publisher,
            poll_interval_seconds=app_settings.outbox_poll_interval_seconds,
            batch_size=app_settings.outbox_batch_size,
        )
        outbox_task = asyncio.create_task(outbox_dispatcher.run_forever())

        app.state.settings = app_settings
        app.state.database_manager = database_manager
        app.state.reference_validator = app_reference_validator
        app.state.timetable_event_publisher = app_timetable_event_publisher
        app.state.outbox_dispatcher = outbox_dispatcher

        yield
        outbox_dispatcher.stop()
        await outbox_task
        await app_timetable_event_publisher.close()
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
    app.include_router(timetable_router)
    app.include_router(appointment_router)
    return app


app = create_app()
