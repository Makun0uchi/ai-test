from collections.abc import Iterator
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from services.account_service.app.core.config import Settings
from services.account_service.app.main import create_app


@pytest.fixture()
def client(tmp_path) -> Iterator[TestClient]:
    settings = Settings(
        DATABASE_URL=f"sqlite+pysqlite:///{tmp_path / 'account-service.db'}",
        JWT_SECRET_KEY="test-secret-key",
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
    settings = cast(Settings, cast(Any, client.app).state.settings)

    unauthorized = client.get("/internal/accounts/1")
    assert unauthorized.status_code == 401

    response = client.get("/internal/accounts/4", headers=_internal_headers(settings))
    assert response.status_code == 200
    assert response.json() == {"id": 4, "username": "user", "roles": ["User"]}
