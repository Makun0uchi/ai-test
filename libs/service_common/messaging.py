from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar, cast

import aio_pika
from pydantic import BaseModel

from .logging import get_correlation_id, log_event, reset_correlation_id, set_correlation_id

LOGGER = logging.getLogger("simbir.health.messaging")


def _header_as_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _header_as_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


@dataclass(slots=True)
class EventMessage:
    event_type: str
    routing_key: str
    payload: dict[str, Any]
    correlation_id: str | None = None
    aggregate_type: str | None = None
    aggregate_id: int | None = None


EventHandler = Callable[[EventMessage], Awaitable[None]]


class EventPublisher(Protocol):
    async def publish(self, message: EventMessage) -> None: ...

    async def close(self) -> None: ...


class EventSubscriber(Protocol):
    failed_messages: list[EventMessage]
    dead_letter_messages: list[EventMessage]

    async def prepare(self) -> None: ...

    async def consume(
        self,
        *,
        handler: EventHandler,
        stop_event: asyncio.Event,
    ) -> None: ...

    async def close(self) -> None: ...


class InMemoryTopicBroker:
    def __init__(self) -> None:
        self.published_messages: list[EventMessage] = []
        self._subscribers: list[InMemoryTopicSubscriber] = []

    async def publish(self, message: EventMessage) -> None:
        if message.correlation_id is None:
            message.correlation_id = get_correlation_id()
        log_event(
            "event published",
            correlation_id=message.correlation_id,
            event_type=message.event_type,
            routing_key=message.routing_key,
            aggregate_type=message.aggregate_type,
            aggregate_id=message.aggregate_id,
        )
        self.published_messages.append(message)
        for subscriber in list(self._subscribers):
            if subscriber.matches(message.routing_key):
                await subscriber.enqueue(message)

    def create_subscriber(
        self,
        *,
        queue_name: str,
        routing_keys: tuple[str, ...],
        dead_letter_queue_name: str | None = None,
    ) -> InMemoryTopicSubscriber:
        return InMemoryTopicSubscriber(
            broker=self,
            queue_name=queue_name,
            routing_keys=routing_keys,
            dead_letter_queue_name=dead_letter_queue_name,
        )

    async def close(self) -> None:
        return None

    def register(self, subscriber: InMemoryTopicSubscriber) -> None:
        if subscriber not in self._subscribers:
            self._subscribers.append(subscriber)

    def unregister(self, subscriber: InMemoryTopicSubscriber) -> None:
        if subscriber in self._subscribers:
            self._subscribers.remove(subscriber)


class InMemoryTopicSubscriber:
    def __init__(
        self,
        *,
        broker: InMemoryTopicBroker,
        queue_name: str,
        routing_keys: tuple[str, ...],
        dead_letter_queue_name: str | None = None,
    ) -> None:
        self.broker = broker
        self.queue_name = queue_name
        self.routing_keys = routing_keys
        self.dead_letter_queue_name = dead_letter_queue_name
        self.failed_messages: list[EventMessage] = []
        self.dead_letter_messages: list[EventMessage] = []
        self._queue: asyncio.Queue[EventMessage] = asyncio.Queue()
        self._prepared = False

    async def prepare(self) -> None:
        if not self._prepared:
            self.broker.register(self)
            self._prepared = True

    async def consume(
        self,
        *,
        handler: EventHandler,
        stop_event: asyncio.Event,
    ) -> None:
        while True:
            if stop_event.is_set() and self._queue.empty():
                break
            try:
                message = await asyncio.wait_for(self._queue.get(), timeout=0.1)
            except TimeoutError:
                continue

            try:
                await handler(message)
            except Exception:
                self.failed_messages.append(message)
                self.dead_letter_messages.append(message)
                log_event(
                    "event handler failed",
                    correlation_id=message.correlation_id,
                    event_type=message.event_type,
                    routing_key=message.routing_key,
                    aggregate_type=message.aggregate_type,
                    aggregate_id=message.aggregate_id,
                    queue_name=self.queue_name,
                    dead_letter_queue_name=self.dead_letter_queue_name,
                )
                LOGGER.exception(
                    "In-memory event handler failed",
                    extra={
                        "correlation_id": message.correlation_id,
                        "queue_name": self.queue_name,
                        "event_type": message.event_type,
                        "routing_key": message.routing_key,
                        "aggregate_type": message.aggregate_type,
                        "aggregate_id": message.aggregate_id,
                        "dead_letter_queue_name": self.dead_letter_queue_name,
                    },
                )

    async def close(self) -> None:
        if self._prepared:
            self.broker.unregister(self)
            self._prepared = False

    def matches(self, routing_key: str) -> bool:
        return routing_key in self.routing_keys

    async def enqueue(self, message: EventMessage) -> None:
        await self._queue.put(message)


class RabbitMQTopicPublisher:
    def __init__(self, *, url: str, exchange_name: str) -> None:
        self.url = url
        self.exchange_name = exchange_name
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None

    async def publish(self, message: EventMessage) -> None:
        if message.correlation_id is None:
            message.correlation_id = get_correlation_id()
        exchange = await self._get_exchange()
        body = json.dumps(message.payload, ensure_ascii=False).encode("utf-8")
        log_event(
            "event published",
            correlation_id=message.correlation_id,
            event_type=message.event_type,
            routing_key=message.routing_key,
            aggregate_type=message.aggregate_type,
            aggregate_id=message.aggregate_id,
        )
        await exchange.publish(
            aio_pika.Message(
                body=body,
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                type=message.event_type,
                correlation_id=message.correlation_id,
                headers={
                    "aggregate_type": message.aggregate_type,
                    "aggregate_id": message.aggregate_id,
                },
            ),
            routing_key=message.routing_key,
        )

    async def close(self) -> None:
        if self._channel is not None and not self._channel.is_closed:
            await self._channel.close()
        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()

    async def _get_exchange(self) -> aio_pika.abc.AbstractExchange:
        if self._exchange is not None:
            return self._exchange

        self._connection = await aio_pika.connect_robust(self.url)
        channel = await self._connection.channel()
        self._channel = channel
        self._exchange = await channel.declare_exchange(
            self.exchange_name,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )
        return self._exchange


class RabbitMQTopicSubscriber:
    def __init__(
        self,
        *,
        url: str,
        exchange_name: str,
        queue_name: str,
        routing_keys: tuple[str, ...],
        dead_letter_exchange_name: str | None = None,
        dead_letter_queue_name: str | None = None,
    ) -> None:
        self.url = url
        self.exchange_name = exchange_name
        self.queue_name = queue_name
        self.routing_keys = routing_keys
        self.dead_letter_exchange_name = dead_letter_exchange_name
        self.dead_letter_queue_name = dead_letter_queue_name
        self.failed_messages: list[EventMessage] = []
        self.dead_letter_messages: list[EventMessage] = []
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._queue: aio_pika.abc.AbstractQueue | None = None

    async def prepare(self) -> None:
        await self._get_queue()

    async def consume(
        self,
        *,
        handler: EventHandler,
        stop_event: asyncio.Event,
    ) -> None:
        queue = await self._get_queue()
        while not stop_event.is_set():
            try:
                incoming_message = await queue.get(timeout=0.1, fail=False)
            except TimeoutError:
                continue
            if incoming_message is None:
                continue

            payload = json.loads(incoming_message.body.decode("utf-8"))
            headers = incoming_message.headers or {}
            message = EventMessage(
                event_type=incoming_message.type or payload["eventType"],
                routing_key=incoming_message.routing_key or "",
                payload=payload,
                correlation_id=incoming_message.correlation_id,
                aggregate_type=_header_as_str(headers.get("aggregate_type")),
                aggregate_id=_header_as_int(headers.get("aggregate_id")),
            )
            try:
                await handler(message)
            except Exception:
                self.failed_messages.append(message)
                self.dead_letter_messages.append(message)
                log_event(
                    "event handler failed",
                    correlation_id=message.correlation_id,
                    event_type=message.event_type,
                    routing_key=message.routing_key,
                    aggregate_type=message.aggregate_type,
                    aggregate_id=message.aggregate_id,
                    queue_name=self.queue_name,
                    dead_letter_queue_name=self.dead_letter_queue_name,
                )
                LOGGER.exception(
                    "RabbitMQ event handler failed",
                    extra={
                        "correlation_id": message.correlation_id,
                        "queue_name": self.queue_name,
                        "event_type": message.event_type,
                        "routing_key": message.routing_key,
                        "aggregate_type": message.aggregate_type,
                        "aggregate_id": message.aggregate_id,
                        "dead_letter_queue_name": self.dead_letter_queue_name,
                    },
                )
                await incoming_message.nack(requeue=False)
                continue

            await incoming_message.ack()

    async def close(self) -> None:
        if self._channel is not None and not self._channel.is_closed:
            await self._channel.close()
        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()

    async def _get_queue(self) -> aio_pika.abc.AbstractQueue:
        if self._queue is not None:
            return self._queue

        self._connection = await aio_pika.connect_robust(self.url)
        channel = await self._connection.channel()
        self._channel = channel
        exchange = await channel.declare_exchange(
            self.exchange_name,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )
        queue_arguments: aio_pika.abc.Arguments = None
        if self.dead_letter_exchange_name and self.dead_letter_queue_name:
            dead_letter_exchange = await channel.declare_exchange(
                self.dead_letter_exchange_name,
                aio_pika.ExchangeType.DIRECT,
                durable=True,
            )
            dead_letter_queue = await channel.declare_queue(
                self.dead_letter_queue_name,
                durable=True,
            )
            await dead_letter_queue.bind(
                dead_letter_exchange,
                routing_key=self.dead_letter_queue_name,
            )
            queue_arguments = cast(
                aio_pika.abc.Arguments,
                {
                    "x-dead-letter-exchange": self.dead_letter_exchange_name,
                    "x-dead-letter-routing-key": self.dead_letter_queue_name,
                },
            )
        self._queue = await channel.declare_queue(
            self.queue_name,
            durable=True,
            arguments=queue_arguments,
        )
        for routing_key in self.routing_keys:
            await self._queue.bind(exchange, routing_key=routing_key)
        return self._queue


EventContract = TypeVar("EventContract", bound=BaseModel)


def parse_event_payload(message: EventMessage, event_model: type[EventContract]) -> EventContract:
    return event_model.model_validate(message.payload)


class BackgroundEventConsumer:
    def __init__(
        self,
        *,
        name: str,
        subscriber: EventSubscriber,
        handler: EventHandler,
    ) -> None:
        self.name = name
        self.subscriber = subscriber
        self.handler = handler
        self._stop_event = asyncio.Event()
        self._logger = logging.getLogger(f"simbir.health.consumer.{name}")

    async def prepare(self) -> None:
        await self.subscriber.prepare()

    async def run_forever(self) -> None:
        self._logger.info("Starting event consumer")
        await self.subscriber.consume(handler=self._handle_message, stop_event=self._stop_event)
        self._logger.info("Event consumer stopped")

    def stop(self) -> None:
        self._stop_event.set()

    async def _handle_message(self, message: EventMessage) -> None:
        token = set_correlation_id(message.correlation_id)
        try:
            self._logger.info(
                "handling event",
                extra={
                    "correlation_id": message.correlation_id,
                    "event_type": message.event_type,
                    "routing_key": message.routing_key,
                    "aggregate_type": message.aggregate_type,
                    "aggregate_id": message.aggregate_id,
                },
            )
            await self.handler(message)
        finally:
            reset_correlation_id(token)
