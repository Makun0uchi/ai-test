from __future__ import annotations

from typing import Protocol

SUPPORTED_SERVICE_ENVS = frozenset({"local", "ci", "staging", "production"})
PRODUCTION_LIKE_ENVS = frozenset({"staging", "production"})


class EnvironmentSettings(Protocol):
    service_name: str
    service_env: str


def validate_service_environment(settings: EnvironmentSettings) -> None:
    if settings.service_env not in SUPPORTED_SERVICE_ENVS:
        supported = ", ".join(sorted(SUPPORTED_SERVICE_ENVS))
        raise ValueError(
            f"{settings.service_name} has unsupported SERVICE_ENV={settings.service_env!r}; "
            f"supported values: {supported}"
        )


def is_production_like(service_env: str) -> bool:
    return service_env in PRODUCTION_LIKE_ENVS
