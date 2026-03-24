from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

import aio_pika


@dataclass(slots=True)
class AccountEventMessage:
    event_type: str
    routing_key: str
    payload: dict[str, Any]


class AccountEventPublisher(Protocol):
    async def publish(self, message: AccountEventMessage) -> None: ...

    async def close(self) -> None: ...


class InMemoryAccountEventPublisher:
    def __init__(self) -> None:
        self.published_messages: list[AccountEventMessage] = []

    async def publish(self, message: AccountEventMessage) -> None:
        self.published_messages.append(message)

    async def close(self) -> None:
        return None


class RabbitMQAccountEventPublisher:
    def __init__(self, *, url: str, exchange_name: str) -> None:
        self.url = url
        self.exchange_name = exchange_name
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None

    async def publish(self, message: AccountEventMessage) -> None:
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
