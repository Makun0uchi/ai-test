from __future__ import annotations

from typing import Protocol

from fastapi import HTTPException, status

from .environment import is_production_like

DEFAULT_JWT_SECRET_KEY = "local-account-service-secret"
DEFAULT_INTERNAL_API_KEY = "local-internal-api-key"
MIN_SECRET_LENGTH = 32


class SecuritySettings(Protocol):
    service_name: str
    service_env: str
    jwt_secret_key: str
    jwt_algorithm: str
    internal_api_key: str


def validate_security_settings(settings: SecuritySettings) -> None:
    if not is_production_like(settings.service_env):
        return

    issues: list[str] = []
    if settings.jwt_secret_key == DEFAULT_JWT_SECRET_KEY:
        issues.append("JWT_SECRET_KEY must not use the local default value")
    elif len(settings.jwt_secret_key) < MIN_SECRET_LENGTH:
        issues.append(
            f"JWT_SECRET_KEY must be at least {MIN_SECRET_LENGTH} characters in "
            f"{settings.service_env}"
        )

    if settings.internal_api_key == DEFAULT_INTERNAL_API_KEY:
        issues.append("INTERNAL_API_KEY must not use the local default value")
    elif len(settings.internal_api_key) < MIN_SECRET_LENGTH:
        issues.append(
            f"INTERNAL_API_KEY must be at least {MIN_SECRET_LENGTH} characters in "
            f"{settings.service_env}"
        )

    if settings.jwt_algorithm != "HS256":
        issues.append(
            "JWT_ALGORITHM is currently limited to HS256 in runtime code; "
            "see docs/security/jwt_strategy.md for the asymmetric rollout plan"
        )

    if issues:
        message = "; ".join(issues)
        raise ValueError(
            f"{settings.service_name} has insecure configuration for "
            f"{settings.service_env}: {message}"
        )


def ensure_internal_token(
    received_token: str | None,
    *,
    expected_token: str,
) -> None:
    if received_token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal token",
        )
