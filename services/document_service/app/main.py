import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from libs.service_common.logging import configure_logging
from libs.service_common.migrations import run_database_migrations
from libs.service_common.reference_validation import HttpReferenceValidator, ReferenceValidator

from .core.config import Settings
from .core.database import DatabaseManager
from .events.dispatcher import HistoryOutboxDispatcher
from .events.indexer import HistorySearchIndexer
from .events.publisher import (
    HistoryEventPublisher,
    HistoryEventSubscriber,
    InMemoryHistoryEventPublisher,
    RabbitMQHistoryEventPublisher,
    RabbitMQHistoryEventSubscriber,
)
from .repositories.history_repository import HistoryRepository
from .routers.history import router as history_router
from .routers.system import router as system_router
from .search.base import SearchGateway
from .search.elasticsearch_gateway import ElasticsearchSearchGateway
from .search.memory_gateway import InMemorySearchGateway
from .services.history_service import HistoryService

SERVICE_ROOT = Path(__file__).resolve().parents[1]
INDEXED_HISTORY_EVENT_TYPES = (
    HistoryService.CREATED_EVENT_TYPE,
    HistoryService.UPDATED_EVENT_TYPE,
)


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


def create_history_event_publisher(settings: Settings) -> HistoryEventPublisher:
    if settings.rabbitmq_url.startswith("memory://"):
        return InMemoryHistoryEventPublisher()
    return RabbitMQHistoryEventPublisher(
        url=settings.rabbitmq_url,
        exchange_name=settings.history_events_exchange,
    )


def create_history_event_subscriber(
    settings: Settings,
    publisher: HistoryEventPublisher,
) -> HistoryEventSubscriber:
    if settings.rabbitmq_url.startswith("memory://") and isinstance(
        publisher, InMemoryHistoryEventPublisher
    ):
        return publisher.create_subscriber(
            queue_name=settings.history_indexer_queue_name,
            routing_keys=INDEXED_HISTORY_EVENT_TYPES,
        )
    return RabbitMQHistoryEventSubscriber(
        url=settings.rabbitmq_url,
        exchange_name=settings.history_events_exchange,
        queue_name=settings.history_indexer_queue_name,
        routing_keys=INDEXED_HISTORY_EVENT_TYPES,
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
    history_event_publisher: HistoryEventPublisher | None = None,
    history_event_subscriber: HistoryEventSubscriber | None = None,
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
        search_gateway = create_search_gateway(app_settings)
        search_gateway.setup()
        app_reference_validator = reference_validator or create_reference_validator(app_settings)
        app_history_event_publisher = history_event_publisher or create_history_event_publisher(
            app_settings
        )
        app_history_event_subscriber = history_event_subscriber or create_history_event_subscriber(
            app_settings,
            app_history_event_publisher,
        )
        history_indexer = HistorySearchIndexer(
            search_gateway=search_gateway,
            subscriber=app_history_event_subscriber,
        )
        await history_indexer.prepare()
        outbox_dispatcher = HistoryOutboxDispatcher(
            database_manager=database_manager,
            publisher=app_history_event_publisher,
            poll_interval_seconds=app_settings.outbox_poll_interval_seconds,
            batch_size=app_settings.outbox_batch_size,
        )
        sync_search_index(database_manager, search_gateway)
        indexer_task = asyncio.create_task(history_indexer.run_forever())
        outbox_task = asyncio.create_task(outbox_dispatcher.run_forever())

        app.state.settings = app_settings
        app.state.database_manager = database_manager
        app.state.search_gateway = search_gateway
        app.state.reference_validator = app_reference_validator
        app.state.history_event_publisher = app_history_event_publisher
        app.state.history_event_subscriber = app_history_event_subscriber
        app.state.history_indexer = history_indexer
        app.state.outbox_dispatcher = outbox_dispatcher

        yield
        history_indexer.stop()
        outbox_dispatcher.stop()
        await asyncio.gather(indexer_task, outbox_task)
        if app_history_event_subscriber is not app_history_event_publisher:
            await app_history_event_subscriber.close()
        await app_history_event_publisher.close()
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
