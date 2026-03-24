import time
from datetime import datetime
from typing import Any, cast

from fastapi.testclient import TestClient
from libs.service_common.messaging import InMemoryTopicBroker
from libs.service_common.reference_validation import HttpReferenceValidator
from services.account_service.app.core.config import Settings as AccountSettings
from services.account_service.app.main import create_app as create_account_app
from services.document_service.app.core.config import Settings as DocumentSettings
from services.document_service.app.main import create_app as create_document_app
from services.hospital_service.app.core.config import Settings as HospitalSettings
from services.hospital_service.app.main import create_app as create_hospital_app
from services.timetable_service.app.core.config import Settings as TimetableSettings
from services.timetable_service.app.main import create_app as create_timetable_app

HISTORY_EVENT_TYPES = ("history.created.v1", "history.updated.v1")


class InternalTestClient:
    def __init__(self, client: TestClient, *, internal_api_key: str) -> None:
        self.client = client
        self.internal_api_key = internal_api_key

    def get(self, path: str) -> Any:
        return self.client.get(path, headers={"X-Internal-Token": self.internal_api_key})

    def close(self) -> None:
        return None


def _sign_in(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/Authentication/SignIn",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return cast(dict[str, str], response.json())


def _sign_up_patient(client: TestClient, *, username: str) -> dict[str, Any]:
    sign_up_response = client.post(
        "/api/Authentication/SignUp",
        json={
            "lastName": "Petrov",
            "firstName": "Petr",
            "username": username,
            "password": "strong-password",
        },
    )
    assert sign_up_response.status_code == 201
    tokens = cast(dict[str, str], sign_up_response.json())
    me_response = client.get("/api/Accounts/Me", headers=_auth_headers(tokens))
    assert me_response.status_code == 200
    return {
        "tokens": tokens,
        "profile": cast(dict[str, Any], me_response.json()),
    }


def _auth_headers(token_pair: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_pair['accessToken']}"}


def _dt(value: str) -> str:
    return datetime.fromisoformat(value).isoformat()


def test_patient_visit_flow_becomes_searchable_end_to_end(tmp_path) -> None:
    broker = InMemoryTopicBroker()
    shared_secret = "test-secret-key"
    shared_internal_api_key = "test-internal-api-key"

    account_settings = AccountSettings(
        DATABASE_URL=f"sqlite+pysqlite:///{tmp_path / 'account-e2e.db'}",
        JWT_SECRET_KEY=shared_secret,
        INTERNAL_API_KEY=shared_internal_api_key,
        RABBITMQ_URL="memory://shared-events",
        outbox_poll_interval_seconds=0.01,
    )
    hospital_settings = HospitalSettings(
        DATABASE_URL=f"sqlite+pysqlite:///{tmp_path / 'hospital-e2e.db'}",
        JWT_SECRET_KEY=shared_secret,
        INTERNAL_API_KEY=shared_internal_api_key,
        RABBITMQ_URL="memory://shared-events",
        outbox_poll_interval_seconds=0.01,
    )
    timetable_settings = TimetableSettings(
        DATABASE_URL=f"sqlite+pysqlite:///{tmp_path / 'timetable-e2e.db'}",
        JWT_SECRET_KEY=shared_secret,
        INTERNAL_API_KEY=shared_internal_api_key,
        RABBITMQ_URL="memory://shared-events",
        outbox_poll_interval_seconds=0.01,
    )
    document_settings = DocumentSettings(
        DATABASE_URL=f"sqlite+pysqlite:///{tmp_path / 'document-e2e.db'}",
        JWT_SECRET_KEY=shared_secret,
        INTERNAL_API_KEY=shared_internal_api_key,
        ELASTICSEARCH_URL="memory://history-e2e",
        RABBITMQ_URL="memory://shared-events",
        outbox_poll_interval_seconds=0.01,
    )

    with TestClient(
        create_account_app(account_settings, account_event_publisher=broker)
    ) as account_client:
        with TestClient(
            create_hospital_app(hospital_settings, hospital_event_publisher=broker)
        ) as hospital_client:
            timetable_reference_validator = HttpReferenceValidator(
                account_service_url=str(account_client.base_url),
                hospital_service_url=str(hospital_client.base_url),
                internal_api_key=shared_internal_api_key,
                account_client=cast(
                    Any,
                    InternalTestClient(
                        account_client,
                        internal_api_key=shared_internal_api_key,
                    ),
                ),
                hospital_client=cast(
                    Any,
                    InternalTestClient(
                        hospital_client,
                        internal_api_key=shared_internal_api_key,
                    ),
                ),
            )
            document_reference_validator = HttpReferenceValidator(
                account_service_url=str(account_client.base_url),
                hospital_service_url=str(hospital_client.base_url),
                internal_api_key=shared_internal_api_key,
                account_client=cast(
                    Any,
                    InternalTestClient(
                        account_client,
                        internal_api_key=shared_internal_api_key,
                    ),
                ),
                hospital_client=cast(
                    Any,
                    InternalTestClient(
                        hospital_client,
                        internal_api_key=shared_internal_api_key,
                    ),
                ),
            )

            with TestClient(
                create_timetable_app(
                    timetable_settings,
                    reference_validator=timetable_reference_validator,
                    timetable_event_publisher=broker,
                    hospital_event_subscriber=broker.create_subscriber(
                        queue_name=timetable_settings.hospital_cleanup_queue_name,
                        routing_keys=("hospital.deleted.v1",),
                    ),
                )
            ) as timetable_client:
                with TestClient(
                    create_document_app(
                        document_settings,
                        reference_validator=document_reference_validator,
                        history_event_publisher=broker,
                        history_event_subscriber=broker.create_subscriber(
                            queue_name=document_settings.history_indexer_queue_name,
                            routing_keys=HISTORY_EVENT_TYPES,
                        ),
                    )
                ) as document_client:
                    manager_tokens = _sign_in(account_client, "manager", "manager")
                    doctor_tokens = _sign_in(account_client, "doctor", "doctor")
                    patient = _sign_up_patient(account_client, username="patient.e2e")
                    patient_tokens = cast(dict[str, str], patient["tokens"])
                    patient_profile = cast(dict[str, Any], patient["profile"])

                    doctor_me = account_client.get(
                        "/api/Accounts/Me",
                        headers=_auth_headers(doctor_tokens),
                    )
                    assert doctor_me.status_code == 200
                    doctor_profile = cast(dict[str, Any], doctor_me.json())

                    create_hospital_response = hospital_client.post(
                        "/api/Hospitals",
                        headers=_auth_headers(manager_tokens),
                        json={
                            "name": "Central Hospital",
                            "address": "Lenina 10",
                            "contactPhone": "+7-999-000-11-22",
                            "rooms": ["101", "102"],
                        },
                    )
                    assert create_hospital_response.status_code == 201
                    hospital = cast(dict[str, Any], create_hospital_response.json())

                    create_timetable_response = timetable_client.post(
                        "/api/Timetable",
                        headers=_auth_headers(manager_tokens),
                        json={
                            "hospitalId": hospital["id"],
                            "doctorId": doctor_profile["id"],
                            "from": _dt("2026-03-24T10:00:00"),
                            "to": _dt("2026-03-24T11:00:00"),
                            "room": "101",
                        },
                    )
                    assert create_timetable_response.status_code == 201
                    timetable = cast(dict[str, Any], create_timetable_response.json())

                    create_appointment_response = timetable_client.post(
                        f"/api/Timetable/{timetable['id']}/Appointments",
                        headers=_auth_headers(patient_tokens),
                        json={"time": _dt("2026-03-24T10:00:00")},
                    )
                    assert create_appointment_response.status_code == 201
                    appointment = cast(dict[str, Any], create_appointment_response.json())
                    assert appointment["patientId"] == patient_profile["id"]

                    create_history_response = document_client.post(
                        "/api/History",
                        headers=_auth_headers(doctor_tokens),
                        json={
                            "date": _dt("2026-03-24T10:15:00"),
                            "pacientId": patient_profile["id"],
                            "hospitalId": hospital["id"],
                            "doctorId": doctor_profile["id"],
                            "room": "101",
                            "data": "Пациент жалуется на кашель и боль в горле",
                        },
                    )
                    assert create_history_response.status_code == 201
                    history = cast(dict[str, Any], create_history_response.json())
                    assert history["pacientId"] == patient_profile["id"]

                    history_list_response = document_client.get(
                        f"/api/History/Account/{patient_profile['id']}",
                        headers=_auth_headers(patient_tokens),
                    )
                    assert history_list_response.status_code == 200
                    assert len(history_list_response.json()) == 1

                    deadline = time.time() + 1.5
                    search_payload: dict[str, Any] = {"total": 0, "items": []}
                    while time.time() < deadline:
                        search_response = document_client.get(
                            "/api/History/Search",
                            params={"query": "кашель"},
                            headers=_auth_headers(patient_tokens),
                        )
                        assert search_response.status_code == 200
                        search_payload = cast(dict[str, Any], search_response.json())
                        if search_payload["total"] == 1:
                            break
                        time.sleep(0.02)

                    assert search_payload["total"] == 1
                    assert search_payload["items"][0]["id"] == history["id"]
                    assert search_payload["items"][0]["pacientId"] == patient_profile["id"]
