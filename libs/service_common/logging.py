import logging

from pythonjsonlogger.json import JsonFormatter


def configure_logging(service_name: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s %(service)s")
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    service_logger = logging.getLogger(service_name)
    adapter = logging.LoggerAdapter(service_logger, {"service": service_name})
    adapter.info("logging configured")
