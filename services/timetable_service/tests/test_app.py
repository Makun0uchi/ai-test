from collections.abc import Iterator
from datetime import datetime
from typing import Any, cast

import jwt
import pytest
from fastapi.testclient import TestClient

from services.timetable_service.app.core.config import Settings
from services.timetable_service.app.main import create_app


@pytest.fixture()
def client(tmp_path) -> Iterator[TestClient]:
    settings = Settings(
        DATABASE_URL=f"sqlite+pysqlite:///{tmp_path / 'timetable-service.db'}",
        JWT_SECRET_KEY="test-secret-key",
    )

    with TestClient(create_app(settings)) as test_client:
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


def _dt(value: str) -> str:
    return datetime.fromisoformat(value).isoformat()


def test_health_endpoint_exposes_service_metadata(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "timetable-service"
    assert payload["status"] == "ok"
    assert payload["version"]


def test_swagger_ui_is_exposed_on_required_path(client: TestClient) -> None:
    response = client.get("/ui-swagger")

    assert response.status_code == 200
    assert "Simbir.Health Timetable Service" in response.text


def test_manager_can_create_update_and_query_timetable(client: TestClient) -> None:
    settings = _settings(client)
    create_response = client.post(
        "/api/Timetable",
        headers=_headers(settings, ["Manager"]),
        json={
            "hospitalId": 1,
            "doctorId": 5,
            "from": _dt("2026-03-24T10:00:00"),
            "to": _dt("2026-03-24T12:00:00"),
            "room": "101",
        },
    )

    assert create_response.status_code == 201
    timetable = create_response.json()

    hospital_query = client.get(
        "/api/Timetable/Hospital/1",
        params={"from": _dt("2026-03-24T09:00:00"), "to": _dt("2026-03-24T13:00:00")},
        headers=_headers(settings, ["User"]),
    )
    assert hospital_query.status_code == 200
    assert hospital_query.json()[0]["id"] == timetable["id"]

    doctor_query = client.get(
        "/api/Timetable/Doctor/5",
        params={"from": _dt("2026-03-24T09:00:00"), "to": _dt("2026-03-24T13:00:00")},
        headers=_headers(settings, ["Doctor"]),
    )
    assert doctor_query.status_code == 200
    assert doctor_query.json()[0]["room"] == "101"

    room_query = client.get(
        "/api/Timetable/Hospital/1/Room/101",
        params={"from": _dt("2026-03-24T09:00:00"), "to": _dt("2026-03-24T13:00:00")},
        headers=_headers(settings, ["Doctor"]),
    )
    assert room_query.status_code == 200
    assert room_query.json()[0]["doctorId"] == 5

    update_response = client.put(
        f"/api/Timetable/{timetable['id']}",
        headers=_headers(settings, ["Admin"]),
        json={
            "hospitalId": 1,
            "doctorId": 5,
            "from": _dt("2026-03-24T10:30:00"),
            "to": _dt("2026-03-24T12:30:00"),
            "room": "102",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["room"] == "102"


def test_invalid_timetable_interval_is_rejected(client: TestClient) -> None:
    settings = _settings(client)
    response = client.post(
        "/api/Timetable",
        headers=_headers(settings, ["Manager"]),
        json={
            "hospitalId": 1,
            "doctorId": 5,
            "from": _dt("2026-03-24T10:15:00"),
            "to": _dt("2026-03-24T12:00:00"),
            "room": "101",
        },
    )

    assert response.status_code == 400


def test_overlapping_timetable_is_rejected(client: TestClient) -> None:
    settings = _settings(client)
    first_response = client.post(
        "/api/Timetable",
        headers=_headers(settings, ["Manager"]),
        json={
            "hospitalId": 1,
            "doctorId": 5,
            "from": _dt("2026-03-24T10:00:00"),
            "to": _dt("2026-03-24T11:00:00"),
            "room": "101",
        },
    )
    assert first_response.status_code == 201

    overlap_response = client.post(
        "/api/Timetable",
        headers=_headers(settings, ["Manager"]),
        json={
            "hospitalId": 1,
            "doctorId": 5,
            "from": _dt("2026-03-24T10:30:00"),
            "to": _dt("2026-03-24T11:30:00"),
            "room": "101",
        },
    )

    assert overlap_response.status_code == 409


def test_user_can_book_and_cancel_appointment(client: TestClient) -> None:
    settings = _settings(client)
    create_response = client.post(
        "/api/Timetable",
        headers=_headers(settings, ["Manager"]),
        json={
            "hospitalId": 2,
            "doctorId": 6,
            "from": _dt("2026-03-24T14:00:00"),
            "to": _dt("2026-03-24T15:30:00"),
            "room": "201",
        },
    )
    timetable_id = create_response.json()["id"]

    available_before = client.get(
        f"/api/Timetable/{timetable_id}/Appointments",
        headers=_headers(settings, ["User"], subject=11),
    )
    assert available_before.status_code == 200
    assert available_before.json() == [
        _dt("2026-03-24T14:00:00"),
        _dt("2026-03-24T14:30:00"),
        _dt("2026-03-24T15:00:00"),
    ]

    booking_response = client.post(
        f"/api/Timetable/{timetable_id}/Appointments",
        headers=_headers(settings, ["User"], subject=11),
        json={"time": _dt("2026-03-24T14:30:00")},
    )
    assert booking_response.status_code == 201
    appointment = booking_response.json()
    assert appointment["patientId"] == 11

    duplicate_booking = client.post(
        f"/api/Timetable/{timetable_id}/Appointments",
        headers=_headers(settings, ["User"], subject=12),
        json={"time": _dt("2026-03-24T14:30:00")},
    )
    assert duplicate_booking.status_code == 409

    available_after = client.get(
        f"/api/Timetable/{timetable_id}/Appointments",
        headers=_headers(settings, ["User"], subject=11),
    )
    assert available_after.status_code == 200
    assert available_after.json() == [
        _dt("2026-03-24T14:00:00"),
        _dt("2026-03-24T15:00:00"),
    ]

    delete_response = client.delete(
        f"/api/Appointment/{appointment['id']}",
        headers=_headers(settings, ["User"], subject=11),
    )
    assert delete_response.status_code == 204


def test_only_user_can_book_appointment(client: TestClient) -> None:
    settings = _settings(client)
    create_response = client.post(
        "/api/Timetable",
        headers=_headers(settings, ["Manager"]),
        json={
            "hospitalId": 2,
            "doctorId": 6,
            "from": _dt("2026-03-24T16:00:00"),
            "to": _dt("2026-03-24T17:00:00"),
            "room": "202",
        },
    )
    timetable_id = create_response.json()["id"]

    response = client.post(
        f"/api/Timetable/{timetable_id}/Appointments",
        headers=_headers(settings, ["Doctor"], subject=6),
        json={"time": _dt("2026-03-24T16:00:00")},
    )
    assert response.status_code == 403


def test_manager_can_delete_by_doctor_and_hospital(client: TestClient) -> None:
    settings = _settings(client)
    first = client.post(
        "/api/Timetable",
        headers=_headers(settings, ["Manager"]),
        json={
            "hospitalId": 3,
            "doctorId": 7,
            "from": _dt("2026-03-24T09:00:00"),
            "to": _dt("2026-03-24T10:00:00"),
            "room": "301",
        },
    )
    second = client.post(
        "/api/Timetable",
        headers=_headers(settings, ["Manager"]),
        json={
            "hospitalId": 4,
            "doctorId": 8,
            "from": _dt("2026-03-24T11:00:00"),
            "to": _dt("2026-03-24T12:00:00"),
            "room": "401",
        },
    )
    assert first.status_code == 201
    assert second.status_code == 201

    delete_doctor = client.delete(
        "/api/Timetable/Doctor/7", headers=_headers(settings, ["Manager"])
    )
    assert delete_doctor.status_code == 204

    doctor_query = client.get(
        "/api/Timetable/Doctor/7",
        params={"from": _dt("2026-03-24T08:00:00"), "to": _dt("2026-03-24T13:00:00")},
        headers=_headers(settings, ["User"]),
    )
    assert doctor_query.status_code == 200
    assert doctor_query.json() == []

    delete_hospital = client.delete(
        "/api/Timetable/Hospital/4", headers=_headers(settings, ["Admin"])
    )
    assert delete_hospital.status_code == 204

    hospital_query = client.get(
        "/api/Timetable/Hospital/4",
        params={"from": _dt("2026-03-24T08:00:00"), "to": _dt("2026-03-24T13:00:00")},
        headers=_headers(settings, ["User"]),
    )
    assert hospital_query.status_code == 200
    assert hospital_query.json() == []
