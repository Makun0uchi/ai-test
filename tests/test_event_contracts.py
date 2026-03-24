import time
from datetime import datetime
from typing import Any, cast

import jwt
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from libs.contracts import (
    AccountChangedEvent,
    AppointmentChangedEvent,
    HistoryChangedEvent,
    HospitalChangedEvent,
    TimetableChangedEvent,
)
from libs.service_common.reference_validation import ReferenceValidator
from services.account_service.app.core.config import Settings as AccountSettings
from services.account_service.app.main import create_app as create_account_app
from services.document_service.app.core.config import Settings as DocumentSettings
from services.document_service.app.main import create_app as create_document_app
from services.hospital_service.app.core.config import Settings as HospitalSettings
from services.hospital_service.app.main import create_app as create_hospital_app
from services.timetable_service.app.core.config import Settings as TimetableSettings
from services.timetable_service.app.main import create_app as create_timetable_app


class TimetableContractReferenceValidator(ReferenceValidator):
    def __init__(self) -> None:
        self.doctors = {5, 6, 7}
        self.hospitals = {1: {"101", "102"}, 2: {"201"}}

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


class DocumentContractReferenceValidator(ReferenceValidator):
    def __init__(self) -> None:
        self.user_accounts = {11, 12}
        self.doctor_accounts = {7}
        self.hospitals = {2: {"201", "202"}}

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


def _wait_for_messages(
    client: TestClient,
    *,
    state_attr: str,
    expected_count: int,
    timeout_seconds: float = 1.0,
) -> list[dict[str, Any]]:
    deadline = time.time() + timeout_seconds
    publisher = getattr(cast(Any, client.app).state, state_attr)
    while time.time() < deadline:
        if len(publisher.published_messages) >= expected_count:
            return [message.payload for message in publisher.published_messages]
        time.sleep(0.02)
    return [message.payload for message in publisher.published_messages]


def _sign_in(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/Authentication/SignIn",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return cast(dict[str, str], response.json())


def _auth_headers(token_pair: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_pair['accessToken']}"}


def _issue_token(
    *,
    secret: str,
    algorithm: str,
    roles: list[str],
    subject: int = 1,
    username: str = "tester",
) -> str:
    payload = {
        "sub": str(subject),
        "username": username,
        "roles": roles,
        "type": "access",
    }
    return cast(str, jwt.encode(payload, secret, algorithm=algorithm))


def _service_headers(
    *,
    secret: str,
    algorithm: str,
    roles: list[str],
    subject: int = 1,
) -> dict[str, str]:
    token = _issue_token(
        secret=secret,
        algorithm=algorithm,
        roles=roles,
        subject=subject,
    )
    return {"Authorization": f"Bearer {token}"}


def _dt(value: str) -> str:
    return datetime.fromisoformat(value).isoformat()


def test_account_event_contracts(tmp_path) -> None:
    settings = AccountSettings(
        DATABASE_URL=f"sqlite+pysqlite:///{tmp_path / 'account-contracts.db'}",
        JWT_SECRET_KEY="test-secret-key",
        RABBITMQ_URL="memory://account-events-contracts",
        outbox_poll_interval_seconds=0.01,
    )

    with TestClient(create_account_app(settings)) as client:
        sign_up_response = client.post(
            "/api/Authentication/SignUp",
            json={
                "lastName": "Ivanov",
                "firstName": "Ivan",
                "username": "ivan.contract",
                "password": "strong-password",
            },
        )
        assert sign_up_response.status_code == 201
        user_tokens = cast(dict[str, str], sign_up_response.json())

        update_me_response = client.put(
            "/api/Accounts/Update",
            headers=_auth_headers(user_tokens),
            json={
                "lastName": "Ivanov",
                "firstName": "Ivan Updated",
                "password": "stronger-password",
            },
        )
        assert update_me_response.status_code == 200

        admin_tokens = _sign_in(client, "admin", "admin")
        admin_headers = _auth_headers(admin_tokens)
        create_response = client.post(
            "/api/Accounts",
            headers=admin_headers,
            json={
                "lastName": "Petrova",
                "firstName": "Anna",
                "username": "anna.contract",
                "password": "secure-pass",
                "roles": ["Manager"],
            },
        )
        assert create_response.status_code == 201
        created_id = create_response.json()["id"]

        update_response = client.put(
            f"/api/Accounts/{created_id}",
            headers=admin_headers,
            json={
                "lastName": "Petrova",
                "firstName": "Anna Maria",
                "username": "anna.contract",
                "password": "secure-pass-2",
                "roles": ["Doctor", "Manager"],
            },
        )
        assert update_response.status_code == 200

        delete_response = client.delete(f"/api/Accounts/{created_id}", headers=admin_headers)
        assert delete_response.status_code == 204

        payloads = _wait_for_messages(
            client,
            state_attr="account_event_publisher",
            expected_count=5,
        )

    events = [AccountChangedEvent.model_validate(payload) for payload in payloads]
    assert [event.event_type for event in events] == [
        "account.created.v1",
        "account.updated.v1",
        "account.created.v1",
        "account.updated.v1",
        "account.deleted.v1",
    ]


def test_hospital_event_contracts(tmp_path) -> None:
    settings = HospitalSettings(
        DATABASE_URL=f"sqlite+pysqlite:///{tmp_path / 'hospital-contracts.db'}",
        JWT_SECRET_KEY="test-secret-key",
        RABBITMQ_URL="memory://hospital-events-contracts",
        outbox_poll_interval_seconds=0.01,
    )

    with TestClient(create_hospital_app(settings)) as client:
        headers = _service_headers(
            secret=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
            roles=["Admin"],
        )

        create_response = client.post(
            "/api/Hospitals",
            headers=headers,
            json={
                "name": "Contract Hospital",
                "address": "Lenina 1",
                "contactPhone": "+7-999-000-00-01",
                "rooms": ["101", "102"],
            },
        )
        assert create_response.status_code == 201
        hospital_id = create_response.json()["id"]

        update_response = client.put(
            f"/api/Hospitals/{hospital_id}",
            headers=headers,
            json={
                "name": "Contract Hospital Updated",
                "address": "Lenina 2",
                "contactPhone": "+7-999-000-00-02",
                "rooms": ["201"],
            },
        )
        assert update_response.status_code == 200

        delete_response = client.delete(f"/api/Hospitals/{hospital_id}", headers=headers)
        assert delete_response.status_code == 204

        payloads = _wait_for_messages(
            client,
            state_attr="hospital_event_publisher",
            expected_count=3,
        )

    events = [HospitalChangedEvent.model_validate(payload) for payload in payloads]
    assert [event.event_type for event in events] == [
        "hospital.created.v1",
        "hospital.updated.v1",
        "hospital.deleted.v1",
    ]


def test_timetable_event_contracts(tmp_path) -> None:
    settings = TimetableSettings(
        DATABASE_URL=f"sqlite+pysqlite:///{tmp_path / 'timetable-contracts.db'}",
        JWT_SECRET_KEY="test-secret-key",
        RABBITMQ_URL="memory://timetable-events-contracts",
        outbox_poll_interval_seconds=0.01,
    )

    with TestClient(
        create_timetable_app(settings, reference_validator=TimetableContractReferenceValidator())
    ) as client:
        manager_headers = _service_headers(
            secret=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
            roles=["Manager"],
        )

        create_response = client.post(
            "/api/Timetable",
            headers=manager_headers,
            json={
                "hospitalId": 1,
                "doctorId": 5,
                "from": _dt("2026-03-24T10:00:00"),
                "to": _dt("2026-03-24T11:00:00"),
                "room": "101",
            },
        )
        assert create_response.status_code == 201
        timetable_id = create_response.json()["id"]

        update_response = client.put(
            f"/api/Timetable/{timetable_id}",
            headers=manager_headers,
            json={
                "hospitalId": 1,
                "doctorId": 5,
                "from": _dt("2026-03-24T10:30:00"),
                "to": _dt("2026-03-24T11:30:00"),
                "room": "102",
            },
        )
        assert update_response.status_code == 200

        user_headers = _service_headers(
            secret=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
            roles=["User"],
            subject=22,
        )
        appointment_response = client.post(
            f"/api/Timetable/{timetable_id}/Appointments",
            headers=user_headers,
            json={"time": _dt("2026-03-24T10:30:00")},
        )
        assert appointment_response.status_code == 201
        appointment_id = appointment_response.json()["id"]

        delete_appointment = client.delete(
            f"/api/Appointment/{appointment_id}",
            headers=user_headers,
        )
        assert delete_appointment.status_code == 204

        delete_timetable = client.delete(
            f"/api/Timetable/{timetable_id}",
            headers=manager_headers,
        )
        assert delete_timetable.status_code == 204

        payloads = _wait_for_messages(
            client,
            state_attr="timetable_event_publisher",
            expected_count=5,
        )

    validated: list[TimetableChangedEvent | AppointmentChangedEvent] = []
    for payload in payloads:
        event_type = payload["eventType"]
        if event_type.startswith("timetable."):
            validated.append(TimetableChangedEvent.model_validate(payload))
        else:
            validated.append(AppointmentChangedEvent.model_validate(payload))

    assert [event.event_type for event in validated] == [
        "timetable.created.v1",
        "timetable.updated.v1",
        "appointment.created.v1",
        "appointment.deleted.v1",
        "timetable.deleted.v1",
    ]


def test_history_event_contracts(tmp_path) -> None:
    settings = DocumentSettings(
        DATABASE_URL=f"sqlite+pysqlite:///{tmp_path / 'document-contracts.db'}",
        JWT_SECRET_KEY="test-secret-key",
        ELASTICSEARCH_URL="memory://history-contracts",
        RABBITMQ_URL="memory://history-events-contracts",
        outbox_poll_interval_seconds=0.01,
    )

    with TestClient(
        create_document_app(settings, reference_validator=DocumentContractReferenceValidator())
    ) as client:
        doctor_headers = _service_headers(
            secret=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
            roles=["Doctor"],
            subject=7,
        )

        create_response = client.post(
            "/api/History",
            headers=doctor_headers,
            json={
                "date": _dt("2026-03-24T12:00:00"),
                "pacientId": 11,
                "hospitalId": 2,
                "doctorId": 7,
                "room": "201",
                "data": "Contract history create",
            },
        )
        assert create_response.status_code == 201
        history_id = create_response.json()["id"]

        update_response = client.put(
            f"/api/History/{history_id}",
            headers=doctor_headers,
            json={
                "date": _dt("2026-03-24T12:30:00"),
                "pacientId": 11,
                "hospitalId": 2,
                "doctorId": 7,
                "room": "201",
                "data": "Contract history update",
            },
        )
        assert update_response.status_code == 200

        payloads = _wait_for_messages(
            client,
            state_attr="history_event_publisher",
            expected_count=2,
        )

    events = [HistoryChangedEvent.model_validate(payload) for payload in payloads]
    assert [event.event_type for event in events] == [
        "history.created.v1",
        "history.updated.v1",
    ]
