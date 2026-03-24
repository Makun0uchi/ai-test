import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from libs.service_common.logging import CorrelationIdMiddleware, configure_logging
from libs.service_common.messaging import EventSubscriber
from libs.service_common.migrations import run_database_migrations
from libs.service_common.reference_validation import HttpReferenceValidator, ReferenceValidator

from .core.config import Settings
from .core.database import DatabaseManager
from .events import HospitalDeletedTimetableCleanupConsumer
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


def create_hospital_event_subscriber(
    settings: Settings,
    timetable_event_publisher: TimetableEventPublisher,
) -> EventSubscriber:
    if settings.rabbitmq_url.startswith("memory://") and isinstance(
        timetable_event_publisher, InMemoryTimetableEventPublisher
    ):
        return timetable_event_publisher.create_subscriber(
            queue_name=settings.hospital_cleanup_queue_name,
            routing_keys=("hospital.deleted.v1",),
            dead_letter_queue_name=settings.hospital_cleanup_dead_letter_queue_name,
        )
    from libs.service_common.messaging import RabbitMQTopicSubscriber

    return RabbitMQTopicSubscriber(
        url=settings.rabbitmq_url,
        exchange_name=settings.timetable_events_exchange,
        queue_name=settings.hospital_cleanup_queue_name,
        routing_keys=("hospital.deleted.v1",),
        dead_letter_exchange_name=settings.rabbitmq_dead_letter_exchange,
        dead_letter_queue_name=settings.hospital_cleanup_dead_letter_queue_name,
    )


def create_app(
    settings: Settings | None = None,
    reference_validator: ReferenceValidator | None = None,
    timetable_event_publisher: TimetableEventPublisher | None = None,
    hospital_event_subscriber: EventSubscriber | None = None,
) -> FastAPI:
    app_settings = settings or Settings()
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
        app_reference_validator = reference_validator or create_reference_validator(app_settings)
        app_timetable_event_publisher = (
            timetable_event_publisher or create_timetable_event_publisher(app_settings)
        )
        app_hospital_event_subscriber = (
            hospital_event_subscriber
            or create_hospital_event_subscriber(
                app_settings,
                app_timetable_event_publisher,
            )
        )
        outbox_dispatcher = TimetableOutboxDispatcher(
            database_manager=database_manager,
            publisher=app_timetable_event_publisher,
            poll_interval_seconds=app_settings.outbox_poll_interval_seconds,
            batch_size=app_settings.outbox_batch_size,
        )
        hospital_cleanup_consumer = HospitalDeletedTimetableCleanupConsumer(
            database_manager=database_manager,
            subscriber=app_hospital_event_subscriber,
        )
        await hospital_cleanup_consumer.prepare()
        outbox_task = asyncio.create_task(outbox_dispatcher.run_forever())
        hospital_cleanup_task = asyncio.create_task(hospital_cleanup_consumer.run_forever())

        app.state.settings = app_settings
        app.state.database_manager = database_manager
        app.state.reference_validator = app_reference_validator
        app.state.timetable_event_publisher = app_timetable_event_publisher
        app.state.hospital_event_subscriber = app_hospital_event_subscriber
        app.state.outbox_dispatcher = outbox_dispatcher
        app.state.hospital_cleanup_consumer = hospital_cleanup_consumer

        yield
        hospital_cleanup_consumer.stop()
        outbox_dispatcher.stop()
        await asyncio.gather(hospital_cleanup_task, outbox_task)
        await app_hospital_event_subscriber.close()
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
    app.add_middleware(CorrelationIdMiddleware)
    app.include_router(system_router)
    app.include_router(timetable_router)
    app.include_router(appointment_router)
    return app


app = create_app()
