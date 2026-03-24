from __future__ import annotations

import logging
import socket
import time
from contextvars import ContextVar, Token
from logging.handlers import SocketHandler
from typing import Any
from uuid import uuid4

from pythonjsonlogger.json import JsonFormatter
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

CORRELATION_ID_HEADER = "X-Correlation-ID"
DEFAULT_LOG_FIELDS = (
    "correlation_id",
    "http_method",
    "http_path",
    "status_code",
    "duration_ms",
    "event_type",
    "routing_key",
    "aggregate_type",
    "aggregate_id",
    "queue_name",
)

_correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class ServiceContextFilter(logging.Filter):
    def __init__(self, service_name: str) -> None:
        super().__init__()
        self.service_name = service_name

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "service"):
            record.service = self.service_name
        if not hasattr(record, "correlation_id"):
            record.correlation_id = get_correlation_id()
        for field in DEFAULT_LOG_FIELDS:
            if not hasattr(record, field):
                setattr(record, field, None)
        return True


class JsonTcpSocketHandler(SocketHandler):
    def makePickle(self, record: logging.LogRecord) -> bytes:  # noqa: N802
        msg = self.format(record) + "\n"
        return msg.encode("utf-8")

    def makeSocket(self, timeout: float = 1.0) -> socket.socket:  # noqa: N802
        assert self.port is not None
        return socket.create_connection((self.host, self.port), timeout)


def configure_logging(
    service_name: str,
    *,
    logstash_host: str | None = None,
    logstash_port: int | None = None,
) -> None:
    formatter = JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(service)s %(correlation_id)s "
        "%(http_method)s %(http_path)s %(status_code)s %(duration_ms)s %(event_type)s "
        "%(routing_key)s %(aggregate_type)s %(aggregate_id)s %(queue_name)s"
    )
    context_filter = ServiceContextFilter(service_name)

    handlers: list[logging.Handler] = []

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(context_filter)
    handlers.append(stream_handler)

    if logstash_host and logstash_port:
        logstash_handler = JsonTcpSocketHandler(logstash_host, logstash_port)
        logstash_handler.setFormatter(formatter)
        logstash_handler.addFilter(context_filter)
        handlers.append(logstash_handler)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)
    for handler in handlers:
        root_logger.addHandler(handler)

    logging.getLogger(service_name).info("logging configured")


def get_correlation_id() -> str | None:
    return _correlation_id_var.get()


def set_correlation_id(correlation_id: str | None) -> Token[str | None]:
    return _correlation_id_var.set(correlation_id)


def reset_correlation_id(token: Token[str | None]) -> None:
    _correlation_id_var.reset(token)


def ensure_correlation_id(candidate: str | None = None) -> str:
    return candidate or str(uuid4())


class CorrelationIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.logger = logging.getLogger("simbir.health.request")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = MutableHeaders(scope=scope)
        correlation_id = ensure_correlation_id(headers.get(CORRELATION_ID_HEADER))
        token = set_correlation_id(correlation_id)
        started_at = time.perf_counter()
        status_code = 500

        async def send_with_correlation(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                response_headers = MutableHeaders(scope=message)
                response_headers[CORRELATION_ID_HEADER] = correlation_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_correlation)
            self.logger.info(
                "request completed",
                extra={
                    "correlation_id": correlation_id,
                    "http_method": scope["method"],
                    "http_path": scope["path"],
                    "status_code": status_code,
                    "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
                },
            )
        except Exception:
            self.logger.exception(
                "request failed",
                extra={
                    "correlation_id": correlation_id,
                    "http_method": scope["method"],
                    "http_path": scope["path"],
                    "status_code": 500,
                    "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
                },
            )
            raise
        finally:
            reset_correlation_id(token)


def log_event(event: str, **extra: Any) -> None:
    logging.getLogger("simbir.health.events").info(event, extra=extra)
