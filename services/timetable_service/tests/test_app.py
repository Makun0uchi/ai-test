import time
from collections.abc import Iterator
from datetime import datetime
from typing import Any, cast

import jwt
import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from libs.service_common.reference_validation import ReferenceValidator

from services.timetable_service.app.core.config import Settings
from services.timetable_service.app.events.publisher import InMemoryTimetableEventPublisher
from services.timetable_service.app.main import create_app


class StubReferenceValidator(ReferenceValidator):
    def __init__(self) -> None:
        self.doctors = {5, 6, 7, 8}
        self.hospitals = {
            1: {"101", "102"},
            2: {"201", "202"},
            3: {"301"},
            4: {"401"},
        }

    def ensure_account_has_role(
        self,
        account_id: int,
        *,
        role: str,
        missing_detail: str,
        wrong_role_detail: str,
    ) -> None:
        if role != "Doctor":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=wrong_role_detail)
        if account_id not in self.doctors:
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
        DATABASE_URL=f"sqlite+pysqlite:///{tmp_path / 'timetable-service.db'}",
        JWT_SECRET_KEY="test-secret-key",
        RABBITMQ_URL="memory://timetable-events-tests",
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


def _dt(value: str) -> str:
    return datetime.fromisoformat(value).isoformat()


def _event_publisher(client: TestClient) -> InMemoryTimetableEventPublisher:
    return cast(
        InMemoryTimetableEventPublisher,
        cast(Any, client.app).state.timetable_event_publisher,
    )


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


def test_unknown_doctor_reference_is_rejected(client: TestClient) -> None:
    settings = _settings(client)
    response = client.post(
        "/api/Timetable",
        headers=_headers(settings, ["Manager"]),
        json={
            "hospitalId": 1,
            "doctorId": 999,
            "from": _dt("2026-03-24T10:00:00"),
            "to": _dt("2026-03-24T11:00:00"),
            "room": "101",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Doctor account not found"


def test_unknown_hospital_room_is_rejected(client: TestClient) -> None:
    settings = _settings(client)
    response = client.post(
        "/api/Timetable",
        headers=_headers(settings, ["Manager"]),
        json={
            "hospitalId": 1,
            "doctorId": 5,
            "from": _dt("2026-03-24T10:00:00"),
            "to": _dt("2026-03-24T11:00:00"),
            "room": "999",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Hospital room not found"


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


def test_timetable_and_appointment_events_are_published_via_outbox(client: TestClient) -> None:
    settings = _settings(client)
    create_response = client.post(
        "/api/Timetable",
        headers=_headers(settings, ["Manager"]),
        json={
            "hospitalId": 1,
            "doctorId": 5,
            "from": _dt("2026-03-24T18:00:00"),
            "to": _dt("2026-03-24T19:00:00"),
            "room": "101",
        },
    )
    assert create_response.status_code == 201
    timetable_id = create_response.json()["id"]

    update_response = client.put(
        f"/api/Timetable/{timetable_id}",
        headers=_headers(settings, ["Manager"]),
        json={
            "hospitalId": 1,
            "doctorId": 5,
            "from": _dt("2026-03-24T18:30:00"),
            "to": _dt("2026-03-24T19:30:00"),
            "room": "102",
        },
    )
    assert update_response.status_code == 200

    appointment_response = client.post(
        f"/api/Timetable/{timetable_id}/Appointments",
        headers=_headers(settings, ["User"], subject=22),
        json={"time": _dt("2026-03-24T18:30:00")},
    )
    assert appointment_response.status_code == 201
    appointment_id = appointment_response.json()["id"]

    delete_appointment = client.delete(
        f"/api/Appointment/{appointment_id}",
        headers=_headers(settings, ["User"], subject=22),
    )
    assert delete_appointment.status_code == 204

    delete_timetable = client.delete(
        f"/api/Timetable/{timetable_id}",
        headers=_headers(settings, ["Manager"]),
    )
    assert delete_timetable.status_code == 204

    payloads = _wait_for_published_messages(client, expected_count=5)
    assert len(payloads) == 5
    assert payloads[0]["eventType"] == "timetable.created.v1"
    assert payloads[0]["timetableId"] == timetable_id
    assert payloads[1]["eventType"] == "timetable.updated.v1"
    assert payloads[1]["timetable"]["room"] == "102"
    assert payloads[2]["eventType"] == "appointment.created.v1"
    assert payloads[2]["appointment"]["timetableId"] == timetable_id
    assert payloads[3]["eventType"] == "appointment.deleted.v1"
    assert payloads[3]["appointmentId"] == appointment_id
    assert payloads[4]["eventType"] == "timetable.deleted.v1"
    assert payloads[4]["timetableId"] == timetable_id


def test_bulk_timetable_delete_events_are_published(client: TestClient) -> None:
    settings = _settings(client)
    first = client.post(
        "/api/Timetable",
        headers=_headers(settings, ["Manager"]),
        json={
            "hospitalId": 3,
            "doctorId": 7,
            "from": _dt("2026-03-24T20:00:00"),
            "to": _dt("2026-03-24T21:00:00"),
            "room": "301",
        },
    )
    second = client.post(
        "/api/Timetable",
        headers=_headers(settings, ["Manager"]),
        json={
            "hospitalId": 4,
            "doctorId": 8,
            "from": _dt("2026-03-24T21:00:00"),
            "to": _dt("2026-03-24T22:00:00"),
            "room": "401",
        },
    )
    assert first.status_code == 201
    assert second.status_code == 201

    timetable_id_one = first.json()["id"]
    timetable_id_two = second.json()["id"]

    delete_doctor = client.delete(
        "/api/Timetable/Doctor/7", headers=_headers(settings, ["Manager"])
    )
    assert delete_doctor.status_code == 204

    delete_hospital = client.delete(
        "/api/Timetable/Hospital/4", headers=_headers(settings, ["Admin"])
    )
    assert delete_hospital.status_code == 204

    payloads = _wait_for_published_messages(client, expected_count=4)
    assert len(payloads) == 4
    assert payloads[2]["eventType"] == "timetable.deleted.v1"
    assert payloads[2]["timetableId"] == timetable_id_one
    assert payloads[3]["eventType"] == "timetable.deleted.v1"
    assert payloads[3]["timetableId"] == timetable_id_two
