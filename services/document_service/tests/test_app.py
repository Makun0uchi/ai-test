import time
from collections.abc import Iterator
from datetime import datetime
from typing import Any, cast

import jwt
import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from libs.service_common.reference_validation import ReferenceValidator

from services.document_service.app.core.config import Settings
from services.document_service.app.events.publisher import InMemoryHistoryEventPublisher
from services.document_service.app.main import create_app


class StubReferenceValidator(ReferenceValidator):
    def __init__(self) -> None:
        self.user_accounts = {11, 13, 15, 21, 22, 31, 32, 41}
        self.doctor_accounts = {7, 8}
        self.hospitals = {
            2: {"201", "202", "203"},
            3: {"204"},
            4: {"301", "302"},
            5: {"401", "402"},
            6: {"501"},
        }

    def ensure_account_has_role(
        self,
        account_id: int,
        *,
        role: str,
        missing_detail: str,
        wrong_role_detail: str,
    ) -> None:
        valid_ids = self.user_accounts if role == "User" else self.doctor_accounts
        if account_id not in valid_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=missing_detail)

    def ensure_hospital_exists(self, hospital_id: int, *, missing_detail: str) -> None:
        if hospital_id not in self.hospitals:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=missing_detail)

    def ensure_hospital_room_exists(
        self,
        hospital_id: int,
        room: str,
        *,
        missing_detail: str,
    ) -> None:
        if room not in self.hospitals.get(hospital_id, set()):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=missing_detail)

    def close(self) -> None:
        return None


@pytest.fixture()
def client(tmp_path) -> Iterator[TestClient]:
    settings = Settings(
        DATABASE_URL=f"sqlite+pysqlite:///{tmp_path / 'document-service.db'}",
        JWT_SECRET_KEY="test-secret-key",
        ELASTICSEARCH_URL="memory://history-tests",
        RABBITMQ_URL="memory://history-events-tests",
        outbox_poll_interval_seconds=0.01,
    )

    with TestClient(
        create_app(settings, reference_validator=StubReferenceValidator())
    ) as test_client:
        yield test_client


def _issue_token(
    *, settings: Settings, roles: list[str], subject: int = 1, username: str = "tester"
) -> str:
    payload = {
        "sub": str(subject),
        "username": username,
        "roles": roles,
        "type": "access",
    }
    return cast(str, jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm))


def _headers(settings: Settings, roles: list[str], subject: int = 1) -> dict[str, str]:
    token = _issue_token(settings=settings, roles=roles, subject=subject)
    return {"Authorization": f"Bearer {token}"}


def _settings(client: TestClient) -> Settings:
    return cast(Settings, cast(Any, client.app).state.settings)


def _create_settings(tmp_path, elasticsearch_url: str = "memory://history-tests") -> Settings:
    return Settings(
        DATABASE_URL=f"sqlite+pysqlite:///{tmp_path / 'document-service.db'}",
        JWT_SECRET_KEY="test-secret-key",
        ELASTICSEARCH_URL=elasticsearch_url,
        RABBITMQ_URL="memory://history-events-tests",
        outbox_poll_interval_seconds=0.01,
    )


def _dt(value: str) -> str:
    return datetime.fromisoformat(value).isoformat()


def _event_publisher(client: TestClient) -> InMemoryHistoryEventPublisher:
    return cast(InMemoryHistoryEventPublisher, cast(Any, client.app).state.history_event_publisher)


def _wait_for_published_messages(
    client: TestClient,
    *,
    expected_count: int,
    timeout_seconds: float = 1.0,
) -> list[dict[str, Any]]:
    deadline = time.time() + timeout_seconds
    publisher = _event_publisher(client)
    while time.time() < deadline:
        if len(publisher.published_messages) >= expected_count:
            return [message.payload for message in publisher.published_messages]
        time.sleep(0.02)
    return [message.payload for message in publisher.published_messages]


def test_health_endpoint_exposes_service_metadata(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "document-service"
    assert payload["status"] == "ok"
    assert payload["version"]


def test_swagger_ui_is_exposed_on_required_path(client: TestClient) -> None:
    response = client.get("/ui-swagger")

    assert response.status_code == 200
    assert "Simbir.Health Document Service" in response.text


def test_doctor_can_create_and_user_can_read_own_history(client: TestClient) -> None:
    settings = _settings(client)
    create_response = client.post(
        "/api/History",
        headers=_headers(settings, ["Doctor"], subject=7),
        json={
            "date": _dt("2026-03-24T12:00:00"),
            "pacientId": 11,
            "hospitalId": 2,
            "doctorId": 7,
            "room": "201",
            "data": "Пациент жалуется на головную боль и температуру",
        },
    )

    assert create_response.status_code == 201
    history = create_response.json()

    own_history = client.get(
        "/api/History/Account/11",
        headers=_headers(settings, ["User"], subject=11),
    )
    assert own_history.status_code == 200
    assert own_history.json()[0]["id"] == history["id"]

    forbidden_history = client.get(
        "/api/History/Account/11",
        headers=_headers(settings, ["User"], subject=12),
    )
    assert forbidden_history.status_code == 403


def test_doctor_can_update_history(client: TestClient) -> None:
    settings = _settings(client)
    create_response = client.post(
        "/api/History",
        headers=_headers(settings, ["Doctor"], subject=7),
        json={
            "date": _dt("2026-03-24T09:00:00"),
            "pacientId": 13,
            "hospitalId": 2,
            "doctorId": 7,
            "room": "202",
            "data": "Первичный осмотр",
        },
    )
    history_id = create_response.json()["id"]

    update_response = client.put(
        f"/api/History/{history_id}",
        headers=_headers(settings, ["Manager"], subject=2),
        json={
            "date": _dt("2026-03-24T09:30:00"),
            "pacientId": 13,
            "hospitalId": 2,
            "doctorId": 7,
            "room": "202",
            "data": "Первичный осмотр, назначено лечение",
        },
    )

    assert update_response.status_code == 200
    assert "назначено лечение" in update_response.json()["data"]


def test_user_cannot_create_history(client: TestClient) -> None:
    settings = _settings(client)
    response = client.post(
        "/api/History",
        headers=_headers(settings, ["User"], subject=11),
        json={
            "date": _dt("2026-03-24T10:00:00"),
            "pacientId": 11,
            "hospitalId": 2,
            "doctorId": 7,
            "room": "203",
            "data": "Попытка создать запись",
        },
    )
    assert response.status_code == 403


def test_unknown_patient_reference_is_rejected(client: TestClient) -> None:
    settings = _settings(client)
    response = client.post(
        "/api/History",
        headers=_headers(settings, ["Doctor"], subject=7),
        json={
            "date": _dt("2026-03-24T10:00:00"),
            "pacientId": 999,
            "hospitalId": 2,
            "doctorId": 7,
            "room": "201",
            "data": "Некорректный пациент",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Patient account not found"


def test_unknown_hospital_room_reference_is_rejected(client: TestClient) -> None:
    settings = _settings(client)
    response = client.post(
        "/api/History",
        headers=_headers(settings, ["Doctor"], subject=7),
        json={
            "date": _dt("2026-03-24T10:00:00"),
            "pacientId": 11,
            "hospitalId": 2,
            "doctorId": 7,
            "room": "999",
            "data": "Некорректная палата",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Hospital room not found"


def test_admin_can_read_any_history_by_id(client: TestClient) -> None:
    settings = _settings(client)
    create_response = client.post(
        "/api/History",
        headers=_headers(settings, ["Doctor"], subject=7),
        json={
            "date": _dt("2026-03-24T11:00:00"),
            "pacientId": 15,
            "hospitalId": 3,
            "doctorId": 7,
            "room": "204",
            "data": "Контрольный осмотр",
        },
    )
    history_id = create_response.json()["id"]

    response = client.get(
        f"/api/History/{history_id}", headers=_headers(settings, ["Admin"], subject=1)
    )
    assert response.status_code == 200
    assert response.json()["pacientId"] == 15


def test_search_returns_relevant_history_for_staff(client: TestClient) -> None:
    settings = _settings(client)
    first = client.post(
        "/api/History",
        headers=_headers(settings, ["Doctor"], subject=7),
        json={
            "date": _dt("2026-03-24T12:00:00"),
            "pacientId": 21,
            "hospitalId": 4,
            "doctorId": 7,
            "room": "301",
            "data": "Сильный кашель и боль в горле",
        },
    )
    second = client.post(
        "/api/History",
        headers=_headers(settings, ["Doctor"], subject=8),
        json={
            "date": _dt("2026-03-24T13:00:00"),
            "pacientId": 22,
            "hospitalId": 4,
            "doctorId": 8,
            "room": "302",
            "data": "Плановый осмотр без жалоб",
        },
    )
    assert first.status_code == 201
    assert second.status_code == 201

    search_response = client.get(
        "/api/History/Search",
        params={"query": "кашель", "hospitalId": 4, "page": 1, "size": 10},
        headers=_headers(settings, ["Doctor"], subject=8),
    )

    assert search_response.status_code == 200
    payload = search_response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["pacientId"] == 21


def test_user_search_is_limited_to_own_history(client: TestClient) -> None:
    settings = _settings(client)
    client.post(
        "/api/History",
        headers=_headers(settings, ["Doctor"], subject=7),
        json={
            "date": _dt("2026-03-24T14:00:00"),
            "pacientId": 31,
            "hospitalId": 5,
            "doctorId": 7,
            "room": "401",
            "data": "Высокая температура и озноб",
        },
    )
    client.post(
        "/api/History",
        headers=_headers(settings, ["Doctor"], subject=7),
        json={
            "date": _dt("2026-03-24T15:00:00"),
            "pacientId": 32,
            "hospitalId": 5,
            "doctorId": 7,
            "room": "402",
            "data": "Высокая температура после операции",
        },
    )

    response = client.get(
        "/api/History/Search",
        params={"query": "температура"},
        headers=_headers(settings, ["User"], subject=31),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["pacientId"] == 31


def test_search_index_is_restored_from_database_on_startup(tmp_path) -> None:
    settings = _create_settings(tmp_path, elasticsearch_url="memory://history-reindex")
    reference_validator = StubReferenceValidator()

    with TestClient(create_app(settings, reference_validator=reference_validator)) as first_client:
        create_response = first_client.post(
            "/api/History",
            headers=_headers(settings, ["Doctor"], subject=7),
            json={
                "date": _dt("2026-03-24T16:00:00"),
                "pacientId": 41,
                "hospitalId": 6,
                "doctorId": 7,
                "room": "501",
                "data": "Повторный прием после лечения кашля",
            },
        )
        assert create_response.status_code == 201

    with TestClient(
        create_app(settings, reference_validator=StubReferenceValidator())
    ) as second_client:
        search_response = second_client.get(
            "/api/History/Search",
            params={"query": "кашля"},
            headers=_headers(settings, ["Doctor"], subject=7),
        )

    assert search_response.status_code == 200
    payload = search_response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["pacientId"] == 41


def test_history_events_are_published_via_outbox(client: TestClient) -> None:
    settings = _settings(client)

    create_response = client.post(
        "/api/History",
        headers=_headers(settings, ["Doctor"], subject=7),
        json={
            "date": _dt("2026-03-24T17:00:00"),
            "pacientId": 11,
            "hospitalId": 2,
            "doctorId": 7,
            "room": "201",
            "data": "РџРѕРІС‚РѕСЂРЅС‹Р№ РѕСЃРјРѕС‚СЂ",
        },
    )
    history_id = create_response.json()["id"]

    update_response = client.put(
        f"/api/History/{history_id}",
        headers=_headers(settings, ["Doctor"], subject=7),
        json={
            "date": _dt("2026-03-24T17:30:00"),
            "pacientId": 11,
            "hospitalId": 2,
            "doctorId": 7,
            "room": "201",
            "data": "РџРѕРІС‚РѕСЂРЅС‹Р№ РѕСЃРјРѕС‚СЂ СЃ РѕР±РЅРѕРІР»РµРЅРёРµРј",
        },
    )

    assert create_response.status_code == 201
    assert update_response.status_code == 200

    payloads = _wait_for_published_messages(client, expected_count=2)
    assert len(payloads) == 2
    assert payloads[0]["eventType"] == "history.created.v1"
    assert payloads[0]["historyId"] == history_id
    assert payloads[1]["eventType"] == "history.updated.v1"
    assert payloads[1]["historyId"] == history_id
