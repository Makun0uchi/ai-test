import asyncio
import time
from datetime import datetime
from typing import Any, cast

import jwt
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from libs.contracts import HospitalChangedEvent
from libs.service_common.messaging import EventMessage, InMemoryTopicBroker, parse_event_payload
from libs.service_common.reference_validation import ReferenceValidator
from services.hospital_service.app.core.config import Settings as HospitalSettings
from services.hospital_service.app.main import create_app as create_hospital_app
from services.timetable_service.app.core.config import Settings as TimetableSettings
from services.timetable_service.app.main import create_app as create_timetable_app


class StubReferenceValidator(ReferenceValidator):
    def __init__(self) -> None:
        self.doctors = {5}
        self.hospitals = {1: {"101"}}

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


def _issue_token(*, secret: str, algorithm: str, roles: list[str], subject: int = 1) -> str:
    payload = {
        "sub": str(subject),
        "username": "tester",
        "roles": roles,
        "type": "access",
    }
    return cast(str, jwt.encode(payload, secret, algorithm=algorithm))


def _headers(*, secret: str, algorithm: str, roles: list[str], subject: int = 1) -> dict[str, str]:
    token = _issue_token(
        secret=secret,
        algorithm=algorithm,
        roles=roles,
        subject=subject,
    )
    return {"Authorization": f"Bearer {token}"}


def _dt(value: str) -> str:
    return datetime.fromisoformat(value).isoformat()


def test_in_memory_subscriber_routes_failures_to_dead_letter_queue() -> None:
    async def scenario() -> None:
        broker = InMemoryTopicBroker()
        subscriber = broker.create_subscriber(
            queue_name="tests.consumer.v1",
            routing_keys=("hospital.deleted.v1",),
            dead_letter_queue_name="tests.consumer.dlq.v1",
        )
        stop_event = asyncio.Event()
        processed: list[int] = []

        async def handler(message: EventMessage) -> None:
            event = parse_event_payload(message, HospitalChangedEvent)
            processed.append(event.hospital_id)
            raise RuntimeError("expected test failure")

        await subscriber.prepare()
        consumer_task = asyncio.create_task(
            subscriber.consume(handler=handler, stop_event=stop_event)
        )
        await broker.publish(
            EventMessage(
                event_type="hospital.created.v1",
                routing_key="hospital.created.v1",
                payload={
                    "eventType": "hospital.created.v1",
                    "hospitalId": 1,
                    "hospital": {
                        "id": 1,
                        "name": "Ignored",
                        "address": "Address",
                        "contactPhone": "+7-900-000-00-00",
                        "rooms": ["101"],
                    },
                },
            )
        )
        await broker.publish(
            EventMessage(
                event_type="hospital.deleted.v1",
                routing_key="hospital.deleted.v1",
                payload={
                    "eventType": "hospital.deleted.v1",
                    "hospitalId": 2,
                    "hospital": {
                        "id": 2,
                        "name": "Deleted",
                        "address": "Address",
                        "contactPhone": "+7-900-000-00-01",
                        "rooms": ["101"],
                    },
                },
            )
        )
        await asyncio.sleep(0.15)
        stop_event.set()
        await consumer_task
        await subscriber.close()

        assert processed == [2]
        assert len(subscriber.failed_messages) == 1
        assert subscriber.failed_messages[0].event_type == "hospital.deleted.v1"
        assert len(subscriber.dead_letter_messages) == 1
        assert subscriber.dead_letter_messages[0].event_type == "hospital.deleted.v1"

    asyncio.run(scenario())


def test_hospital_deleted_event_triggers_timetable_cleanup(tmp_path) -> None:
    broker = InMemoryTopicBroker()
    hospital_settings = HospitalSettings(
        DATABASE_URL=f"sqlite+pysqlite:///{tmp_path / 'hospital-cleanup.db'}",
        JWT_SECRET_KEY="test-secret-key",
        RABBITMQ_URL="memory://shared-events",
        outbox_poll_interval_seconds=0.01,
    )
    timetable_settings = TimetableSettings(
        DATABASE_URL=f"sqlite+pysqlite:///{tmp_path / 'timetable-cleanup.db'}",
        JWT_SECRET_KEY="test-secret-key",
        RABBITMQ_URL="memory://shared-events",
        outbox_poll_interval_seconds=0.01,
    )

    with TestClient(
        create_hospital_app(hospital_settings, hospital_event_publisher=broker)
    ) as hospital_client:
        with TestClient(
            create_timetable_app(
                timetable_settings,
                reference_validator=StubReferenceValidator(),
                timetable_event_publisher=broker,
                hospital_event_subscriber=broker.create_subscriber(
                    queue_name=timetable_settings.hospital_cleanup_queue_name,
                    routing_keys=("hospital.deleted.v1",),
                    dead_letter_queue_name=(
                        timetable_settings.hospital_cleanup_dead_letter_queue_name
                    ),
                ),
            )
        ) as timetable_client:
            hospital_headers = _headers(
                secret=hospital_settings.jwt_secret_key,
                algorithm=hospital_settings.jwt_algorithm,
                roles=["Admin"],
            )
            create_hospital_response = hospital_client.post(
                "/api/Hospitals",
                headers=hospital_headers,
                json={
                    "name": "Cleanup Hospital",
                    "address": "Lenina 1",
                    "contactPhone": "+7-999-000-00-01",
                    "rooms": ["101"],
                },
            )
            assert create_hospital_response.status_code == 201
            hospital_id = create_hospital_response.json()["id"]
            assert hospital_id == 1

            timetable_headers = _headers(
                secret=timetable_settings.jwt_secret_key,
                algorithm=timetable_settings.jwt_algorithm,
                roles=["Manager"],
            )
            create_timetable_response = timetable_client.post(
                "/api/Timetable",
                headers=timetable_headers,
                json={
                    "hospitalId": hospital_id,
                    "doctorId": 5,
                    "from": _dt("2026-03-24T10:00:00"),
                    "to": _dt("2026-03-24T11:00:00"),
                    "room": "101",
                },
            )
            assert create_timetable_response.status_code == 201
            timetable_id = create_timetable_response.json()["id"]

            delete_hospital_response = hospital_client.delete(
                f"/api/Hospitals/{hospital_id}",
                headers=hospital_headers,
            )
            assert delete_hospital_response.status_code == 204

            deadline = time.time() + 1.0
            hospital_query_payload: list[dict[str, Any]] = [{"id": timetable_id}]
            while time.time() < deadline:
                hospital_query = timetable_client.get(
                    f"/api/Timetable/Hospital/{hospital_id}",
                    params={"from": _dt("2026-03-24T09:00:00"), "to": _dt("2026-03-24T12:00:00")},
                    headers=_headers(
                        secret=timetable_settings.jwt_secret_key,
                        algorithm=timetable_settings.jwt_algorithm,
                        roles=["User"],
                    ),
                )
                assert hospital_query.status_code == 200
                hospital_query_payload = cast(list[dict[str, Any]], hospital_query.json())
                if hospital_query_payload == []:
                    break
                time.sleep(0.02)

            assert hospital_query_payload == []
            published_event_types = [message.event_type for message in broker.published_messages]
            assert "hospital.deleted.v1" in published_event_types
            assert "timetable.deleted.v1" in published_event_types
