from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol

import aio_pika


@dataclass(slots=True)
class HistoryEventMessage:
    event_type: str
    routing_key: str
    payload: dict[str, Any]


HistoryEventHandler = Callable[[HistoryEventMessage], Awaitable[None]]


class HistoryEventPublisher(Protocol):
    async def publish(self, message: HistoryEventMessage) -> None: ...

    async def close(self) -> None: ...


class HistoryEventSubscriber(Protocol):
    async def prepare(self) -> None: ...

    async def consume(
        self,
        *,
        handler: HistoryEventHandler,
        stop_event: asyncio.Event,
    ) -> None: ...

    async def close(self) -> None: ...


class InMemoryHistoryEventPublisher:
    def __init__(self) -> None:
        self.published_messages: list[HistoryEventMessage] = []
        self._queue: asyncio.Queue[HistoryEventMessage] = asyncio.Queue()

    async def publish(self, message: HistoryEventMessage) -> None:
        self.published_messages.append(message)
        await self._queue.put(message)

    async def prepare(self) -> None:
        return None

    async def consume(
        self,
        *,
        handler: HistoryEventHandler,
        stop_event: asyncio.Event,
    ) -> None:
        while True:
            if stop_event.is_set() and self._queue.empty():
                break
            try:
                message = await asyncio.wait_for(self._queue.get(), timeout=0.1)
            except TimeoutError:
                continue
            await handler(message)

    async def close(self) -> None:
        return None


class RabbitMQHistoryEventPublisher:
    def __init__(self, *, url: str, exchange_name: str) -> None:
        self.url = url
        self.exchange_name = exchange_name
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None

    async def publish(self, message: HistoryEventMessage) -> None:
        exchange = await self._get_exchange()
        body = json.dumps(message.payload, ensure_ascii=False).encode("utf-8")
        await exchange.publish(
            aio_pika.Message(
                body=body,
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                type=message.event_type,
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


class RabbitMQHistoryEventSubscriber:
    def __init__(
        self,
        *,
        url: str,
        exchange_name: str,
        queue_name: str,
        routing_keys: tuple[str, ...],
    ) -> None:
        self.url = url
        self.exchange_name = exchange_name
        self.queue_name = queue_name
        self.routing_keys = routing_keys
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._queue: aio_pika.abc.AbstractQueue | None = None

    async def prepare(self) -> None:
        await self._get_queue()

    async def consume(
        self,
        *,
        handler: HistoryEventHandler,
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

            async with incoming_message.process():
                payload = json.loads(incoming_message.body.decode("utf-8"))
                await handler(
                    HistoryEventMessage(
                        event_type=incoming_message.type or payload["eventType"],
                        routing_key=incoming_message.routing_key or "",
                        payload=payload,
                    )
                )

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
        self._queue = await channel.declare_queue(self.queue_name, durable=True)
        for routing_key in self.routing_keys:
            await self._queue.bind(exchange, routing_key=routing_key)
        return self._queue
