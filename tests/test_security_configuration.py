import pytest
from libs.service_common.security import (
    DEFAULT_INTERNAL_API_KEY,
    DEFAULT_JWT_SECRET_KEY,
    validate_security_settings,
)
from services.account_service.app.core.config import Settings as AccountSettings
from services.account_service.app.main import create_app


def _settings(**overrides: object) -> AccountSettings:
    payload: dict[str, object] = {
        "service_env": "local",
        "jwt_secret_key": DEFAULT_JWT_SECRET_KEY,
        "internal_api_key": DEFAULT_INTERNAL_API_KEY,
    }
    payload.update(overrides)
    return AccountSettings.model_validate(payload)


def test_local_environment_allows_local_defaults() -> None:
    settings = _settings()

    validate_security_settings(settings)


def test_production_environment_rejects_default_jwt_secret() -> None:
    settings = _settings(
        service_env="production",
        jwt_secret_key=DEFAULT_JWT_SECRET_KEY,
        internal_api_key="x" * 32,
    )

    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        create_app(settings)


def test_production_environment_rejects_short_internal_token() -> None:
    settings = _settings(
        service_env="production",
        jwt_secret_key="y" * 32,
        internal_api_key="short-token",
    )

    with pytest.raises(ValueError, match="INTERNAL_API_KEY"):
        create_app(settings)


def test_production_environment_accepts_strong_explicit_secrets() -> None:
    settings = _settings(
        service_env="production",
        jwt_secret_key="y" * 32,
        internal_api_key="z" * 32,
    )

    app = create_app(settings)

    assert app.title == "Simbir.Health Account Service"
