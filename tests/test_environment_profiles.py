import pytest
from services.account_service.app.core.config import Settings as AccountSettings
from services.account_service.app.main import create_app


def _settings(**overrides: object) -> AccountSettings:
    payload: dict[str, object] = {
        "service_env": "local",
        "jwt_secret_key": "x" * 32,
        "internal_api_key": "y" * 32,
    }
    payload.update(overrides)
    return AccountSettings.model_validate(payload)


def test_supported_service_environment_starts_application() -> None:
    app = create_app(_settings(service_env="ci"))

    assert app.title == "Simbir.Health Account Service"


def test_unsupported_service_environment_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported SERVICE_ENV"):
        create_app(_settings(service_env="docker"))
