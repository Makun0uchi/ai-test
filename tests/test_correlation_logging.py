from typing import Any, cast

from fastapi.testclient import TestClient
from libs.service_common.logging import (
    CORRELATION_ID_HEADER,
    reset_correlation_id,
    set_correlation_id,
)
from libs.service_common.reference_validation import HttpReferenceValidator
from services.account_service.app.core.config import Settings as AccountSettings
from services.account_service.app.main import create_app as create_account_app


class DummyResponse:
    def __init__(self, *, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


class RecordingClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    def get(self, path: str, headers: dict[str, str] | None = None) -> DummyResponse:
        self.calls.append({"path": path, "headers": headers or {}})
        return DummyResponse(status_code=200, payload=self.payload)

    def close(self) -> None:
        return None


def test_http_reference_validator_forwards_correlation_id() -> None:
    account_client = RecordingClient({"id": 5, "username": "doctor", "roles": ["Doctor"]})
    hospital_client = RecordingClient({"id": 2, "name": "Hospital", "rooms": ["101"]})
    validator = HttpReferenceValidator(
        account_service_url="http://account-service",
        hospital_service_url="http://hospital-service",
        internal_api_key="internal-key",
        account_client=cast(Any, account_client),
        hospital_client=cast(Any, hospital_client),
    )

    token = set_correlation_id("corr-reference-123")
    try:
        validator.ensure_account_has_role(
            5,
            role="Doctor",
            missing_detail="Doctor account not found",
            wrong_role_detail="Referenced account is not a doctor",
        )
        validator.ensure_hospital_exists(2, missing_detail="Hospital not found")
    finally:
        reset_correlation_id(token)
        validator.close()

    assert account_client.calls[0]["headers"][CORRELATION_ID_HEADER] == "corr-reference-123"
    assert hospital_client.calls[0]["headers"][CORRELATION_ID_HEADER] == "corr-reference-123"


def test_request_echoes_correlation_id_on_account_service(tmp_path) -> None:
    settings = AccountSettings(
        DATABASE_URL=f"sqlite+pysqlite:///{tmp_path / 'account-correlation.db'}",
        JWT_SECRET_KEY="test-secret-key",
        RABBITMQ_URL="memory://account-correlation-tests",
        outbox_poll_interval_seconds=0.01,
    )

    with TestClient(create_account_app(settings)) as client:
        response = client.get("/health", headers={CORRELATION_ID_HEADER: "corr-health-456"})

    assert response.status_code == 200
    assert response.headers[CORRELATION_ID_HEADER] == "corr-health-456"
