from collections.abc import Iterator
from typing import Any, cast

import jwt
import pytest
from fastapi.testclient import TestClient

from services.hospital_service.app.core.config import Settings
from services.hospital_service.app.main import create_app


@pytest.fixture()
def client(tmp_path) -> Iterator[TestClient]:
    settings = Settings(
        DATABASE_URL=f"sqlite+pysqlite:///{tmp_path / 'hospital-service.db'}",
        JWT_SECRET_KEY="test-secret-key",
    )

    with TestClient(create_app(settings)) as test_client:
        yield test_client


def _issue_token(
    *, settings: Settings, roles: list[str], username: str = "tester", subject: int = 1
) -> str:
    payload = {
        "sub": str(subject),
        "username": username,
        "roles": roles,
        "type": "access",
    }
    return cast(str, jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm))


def _headers(settings: Settings, roles: list[str]) -> dict[str, str]:
    token = _issue_token(settings=settings, roles=roles)
    return {"Authorization": f"Bearer {token}"}


def _settings(client: TestClient) -> Settings:
    return cast(Settings, cast(Any, client.app).state.settings)


def test_health_endpoint_exposes_service_metadata(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "hospital-service"
    assert payload["status"] == "ok"
    assert payload["version"]


def test_swagger_ui_is_exposed_on_required_path(client: TestClient) -> None:
    response = client.get("/ui-swagger")

    assert response.status_code == 200
    assert "Simbir.Health Hospital Service" in response.text


def test_manager_can_create_and_read_hospital(client: TestClient) -> None:
    settings = _settings(client)
    create_response = client.post(
        "/api/Hospitals",
        headers=_headers(settings, ["Manager"]),
        json={
            "name": "Central Hospital",
            "address": "Lenina 10",
            "contactPhone": "+7-999-000-00-00",
            "rooms": ["101", "102"],
        },
    )

    assert create_response.status_code == 201
    hospital = create_response.json()
    assert hospital["rooms"] == ["101", "102"]

    list_response = client.get(
        "/api/Hospitals",
        params={"from": 0, "count": 10},
        headers=_headers(settings, ["User"]),
    )
    assert list_response.status_code == 200
    assert list_response.json()[0]["name"] == "Central Hospital"

    rooms_response = client.get(
        f"/api/Hospitals/{hospital['id']}/Rooms",
        headers=_headers(settings, ["Doctor"]),
    )
    assert rooms_response.status_code == 200
    assert rooms_response.json() == ["101", "102"]


def test_manager_can_update_hospital_and_rooms(client: TestClient) -> None:
    settings = _settings(client)
    create_response = client.post(
        "/api/Hospitals",
        headers=_headers(settings, ["Manager"]),
        json={
            "name": "Regional Hospital",
            "address": "Sovetskaya 5",
            "contactPhone": "+7-999-000-00-01",
            "rooms": ["201"],
        },
    )
    hospital_id = create_response.json()["id"]

    update_response = client.put(
        f"/api/Hospitals/{hospital_id}",
        headers=_headers(settings, ["Admin"]),
        json={
            "name": "Regional Hospital 2",
            "address": "Sovetskaya 15",
            "contactPhone": "+7-999-000-00-02",
            "rooms": ["301", "302"],
        },
    )

    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["name"] == "Regional Hospital 2"
    assert payload["rooms"] == ["301", "302"]


def test_user_cannot_create_hospital(client: TestClient) -> None:
    settings = _settings(client)
    response = client.post(
        "/api/Hospitals",
        headers=_headers(settings, ["User"]),
        json={
            "name": "Unauthorized Hospital",
            "address": "Secret",
            "contactPhone": "+7-999-000-00-03",
            "rooms": ["401"],
        },
    )

    assert response.status_code == 403


def test_duplicate_room_names_are_rejected(client: TestClient) -> None:
    settings = _settings(client)
    response = client.post(
        "/api/Hospitals",
        headers=_headers(settings, ["Manager"]),
        json={
            "name": "Duplicate Rooms Hospital",
            "address": "Mira 1",
            "contactPhone": "+7-999-000-00-04",
            "rooms": ["501", "501"],
        },
    )

    assert response.status_code == 400


def test_manager_can_delete_hospital(client: TestClient) -> None:
    settings = _settings(client)
    create_response = client.post(
        "/api/Hospitals",
        headers=_headers(settings, ["Manager"]),
        json={
            "name": "Delete Hospital",
            "address": "Pushkina 7",
            "contactPhone": "+7-999-000-00-05",
            "rooms": ["601"],
        },
    )
    hospital_id = create_response.json()["id"]

    delete_response = client.delete(
        f"/api/Hospitals/{hospital_id}",
        headers=_headers(settings, ["Manager"]),
    )
    assert delete_response.status_code == 204

    get_response = client.get(
        f"/api/Hospitals/{hospital_id}",
        headers=_headers(settings, ["User"]),
    )
    assert get_response.status_code == 404
