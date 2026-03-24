import time
from collections.abc import Iterator
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from libs.service_common.logging import CORRELATION_ID_HEADER

from services.account_service.app.core.config import Settings
from services.account_service.app.events.publisher import InMemoryAccountEventPublisher
from services.account_service.app.main import create_app


@pytest.fixture()
def client(tmp_path) -> Iterator[TestClient]:
    settings = Settings(
        DATABASE_URL=f"sqlite+pysqlite:///{tmp_path / 'account-service.db'}",
        JWT_SECRET_KEY="test-secret-key",
        RABBITMQ_URL="memory://account-events-tests",
        outbox_poll_interval_seconds=0.01,
    )

    with TestClient(create_app(settings)) as test_client:
        yield test_client


def _sign_in(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/Authentication/SignIn",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return cast(dict[str, str], response.json())


def _auth_headers(token_pair: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_pair['accessToken']}"}


def _internal_headers(settings: Settings) -> dict[str, str]:
    return {"X-Internal-Token": settings.internal_api_key}


def _settings(client: TestClient) -> Settings:
    return cast(Settings, cast(Any, client.app).state.settings)


def _event_publisher(client: TestClient) -> InMemoryAccountEventPublisher:
    return cast(
        InMemoryAccountEventPublisher,
        cast(Any, client.app).state.account_event_publisher,
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
    assert payload["service"] == "account-service"
    assert payload["status"] == "ok"
    assert payload["version"]


def test_swagger_ui_is_exposed_on_required_path(client: TestClient) -> None:
    response = client.get("/ui-swagger")

    assert response.status_code == 200
    assert "Simbir.Health Account Service" in response.text


def test_sign_up_and_me_flow(client: TestClient) -> None:
    sign_up_response = client.post(
        "/api/Authentication/SignUp",
        json={
            "lastName": "Ivanov",
            "firstName": "Ivan",
            "username": "ivan.user",
            "password": "strong-password",
        },
    )

    assert sign_up_response.status_code == 201
    token_pair = cast(dict[str, str], sign_up_response.json())
    me_response = client.get("/api/Accounts/Me", headers=_auth_headers(token_pair))

    assert me_response.status_code == 200
    assert me_response.json()["username"] == "ivan.user"
    assert me_response.json()["roles"] == ["User"]


def test_admin_can_list_create_update_and_delete_accounts(client: TestClient) -> None:
    admin_tokens = _sign_in(client, "admin", "admin")
    headers = _auth_headers(admin_tokens)

    list_response = client.get("/api/Accounts", params={"from": 0, "count": 10}, headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 4

    create_response = client.post(
        "/api/Accounts",
        headers=headers,
        json={
            "lastName": "Petrova",
            "firstName": "Anna",
            "username": "anna.manager",
            "password": "secure-pass",
            "roles": ["Manager"],
        },
    )
    assert create_response.status_code == 201
    created_account = create_response.json()
    assert created_account["roles"] == ["Manager"]

    update_response = client.put(
        f"/api/Accounts/{created_account['id']}",
        headers=headers,
        json={
            "lastName": "Petrova",
            "firstName": "Anastasia",
            "username": "anna.manager",
            "password": "even-better-pass",
            "roles": ["Manager", "Doctor"],
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["firstName"] == "Anastasia"
    assert update_response.json()["roles"] == ["Doctor", "Manager"]

    delete_response = client.delete(f"/api/Accounts/{created_account['id']}", headers=headers)
    assert delete_response.status_code == 204


def test_doctors_directory_is_filtered(client: TestClient) -> None:
    admin_tokens = _sign_in(client, "admin", "admin")
    headers = _auth_headers(admin_tokens)

    response = client.get(
        "/api/Doctors",
        params={"nameFilter": "Doct", "from": 0, "count": 10},
        headers=headers,
    )

    assert response.status_code == 200
    doctors = response.json()
    assert len(doctors) == 1
    assert doctors[0]["username"] == "doctor"


def test_refresh_validate_and_sign_out_flow(client: TestClient) -> None:
    token_pair = _sign_in(client, "user", "user")
    headers = _auth_headers(token_pair)

    validate_response = client.get(
        "/api/Authentication/Validate",
        params={"accessToken": token_pair["accessToken"]},
    )
    assert validate_response.status_code == 200
    assert validate_response.json() == {"isValid": True}

    refresh_response = client.post(
        "/api/Authentication/Refresh",
        json={"refreshToken": token_pair["refreshToken"]},
    )
    assert refresh_response.status_code == 200
    refreshed_pair = cast(dict[str, str], refresh_response.json())
    assert refreshed_pair["refreshToken"] != token_pair["refreshToken"]

    sign_out_response = client.put("/api/Authentication/SignOut", headers=headers)
    assert sign_out_response.status_code == 204

    revoked_refresh_response = client.post(
        "/api/Authentication/Refresh",
        json={"refreshToken": refreshed_pair["refreshToken"]},
    )
    assert revoked_refresh_response.status_code == 401


def test_internal_account_reference_requires_valid_internal_token(client: TestClient) -> None:
    settings = _settings(client)

    unauthorized = client.get("/internal/accounts/1")
    assert unauthorized.status_code == 401

    response = client.get("/internal/accounts/4", headers=_internal_headers(settings))
    assert response.status_code == 200
    assert response.json() == {"id": 4, "username": "user", "roles": ["User"]}


def test_correlation_id_is_echoed_and_persisted_in_account_events(client: TestClient) -> None:
    response = client.post(
        "/api/Authentication/SignUp",
        headers={CORRELATION_ID_HEADER: "corr-account-789"},
        json={
            "lastName": "Smirnov",
            "firstName": "Alexey",
            "username": "alexey.correlation",
            "password": "strong-password",
        },
    )

    assert response.status_code == 201
    assert response.headers[CORRELATION_ID_HEADER] == "corr-account-789"

    publisher = _event_publisher(client)
    payloads = _wait_for_published_messages(client, expected_count=1)
    assert len(payloads) == 1
    assert publisher.published_messages[0].correlation_id == "corr-account-789"


def test_account_events_are_published_via_outbox(client: TestClient) -> None:
    sign_up_response = client.post(
        "/api/Authentication/SignUp",
        json={
            "lastName": "Sidorov",
            "firstName": "Petr",
            "username": "petr.user",
            "password": "strong-password",
        },
    )
    assert sign_up_response.status_code == 201
    user_tokens = cast(dict[str, str], sign_up_response.json())

    update_me_response = client.put(
        "/api/Accounts/Update",
        headers=_auth_headers(user_tokens),
        json={
            "lastName": "Sidorov",
            "firstName": "Petr Updated",
            "password": "new-strong-password",
        },
    )
    assert update_me_response.status_code == 200
    signed_up_account_id = update_me_response.json()["id"]

    admin_tokens = _sign_in(client, "admin", "admin")
    admin_headers = _auth_headers(admin_tokens)

    create_response = client.post(
        "/api/Accounts",
        headers=admin_headers,
        json={
            "lastName": "Petrova",
            "firstName": "Anna",
            "username": "anna.doctor",
            "password": "secure-pass",
            "roles": ["Doctor"],
        },
    )
    assert create_response.status_code == 201
    created_account_id = create_response.json()["id"]

    update_response = client.put(
        f"/api/Accounts/{created_account_id}",
        headers=admin_headers,
        json={
            "lastName": "Petrova",
            "firstName": "Anna Maria",
            "username": "anna.doctor",
            "password": "even-better-pass",
            "roles": ["Doctor", "Manager"],
        },
    )
    assert update_response.status_code == 200

    delete_response = client.delete(f"/api/Accounts/{created_account_id}", headers=admin_headers)
    assert delete_response.status_code == 204

    payloads = _wait_for_published_messages(client, expected_count=5)
    assert len(payloads) == 5
    assert payloads[0]["eventType"] == "account.created.v1"
    assert payloads[0]["account"]["username"] == "petr.user"
    assert payloads[1]["eventType"] == "account.updated.v1"
    assert payloads[1]["accountId"] == signed_up_account_id
    assert payloads[1]["account"]["firstName"] == "Petr Updated"
    assert payloads[2]["eventType"] == "account.created.v1"
    assert payloads[2]["accountId"] == created_account_id
    assert payloads[2]["account"]["roles"] == ["Doctor"]
    assert payloads[3]["eventType"] == "account.updated.v1"
    assert payloads[3]["account"]["roles"] == ["Doctor", "Manager"]
    assert payloads[4]["eventType"] == "account.deleted.v1"
    assert payloads[4]["accountId"] == created_account_id
