import httpx
import pytest
from fastapi import HTTPException
from libs.service_common.reference_validation import HttpReferenceValidator


def test_reference_validator_accepts_existing_doctor_and_room() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/internal/accounts/7":
            return httpx.Response(200, json={"id": 7, "username": "doctor", "roles": ["Doctor"]})
        if request.url.path == "/internal/hospitals/2":
            return httpx.Response(200, json={"id": 2, "name": "Hospital", "rooms": ["201"]})
        if request.url.path == "/internal/hospitals/2/rooms/201":
            return httpx.Response(200, json={"hospitalId": 2, "room": "201"})
        return httpx.Response(404, json={"detail": "Not found"})

    transport = httpx.MockTransport(handler)
    validator = HttpReferenceValidator(
        account_service_url="http://account",
        hospital_service_url="http://hospital",
        internal_api_key="internal-key",
        account_client=httpx.Client(transport=transport, base_url="http://account"),
        hospital_client=httpx.Client(transport=transport, base_url="http://hospital"),
    )

    validator.ensure_account_has_role(
        7,
        role="Doctor",
        missing_detail="Doctor account not found",
        wrong_role_detail="Referenced account is not a doctor",
    )
    validator.ensure_hospital_exists(2, missing_detail="Hospital not found")
    validator.ensure_hospital_room_exists(2, "201", missing_detail="Hospital room not found")

    validator.close()


def test_reference_validator_rejects_wrong_role() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/internal/accounts/11":
            return httpx.Response(200, json={"id": 11, "username": "user", "roles": ["User"]})
        return httpx.Response(404, json={"detail": "Not found"})

    validator = HttpReferenceValidator(
        account_service_url="http://account",
        hospital_service_url="http://hospital",
        internal_api_key="internal-key",
        account_client=httpx.Client(
            transport=httpx.MockTransport(handler),
            base_url="http://account",
        ),
        hospital_client=httpx.Client(
            transport=httpx.MockTransport(handler),
            base_url="http://hospital",
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        validator.ensure_account_has_role(
            11,
            role="Doctor",
            missing_detail="Doctor account not found",
            wrong_role_detail="Referenced account is not a doctor",
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Referenced account is not a doctor"
    validator.close()


def test_reference_validator_maps_upstream_failure_to_service_unavailable() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    validator = HttpReferenceValidator(
        account_service_url="http://account",
        hospital_service_url="http://hospital",
        internal_api_key="internal-key",
        account_client=httpx.Client(
            transport=httpx.MockTransport(handler),
            base_url="http://account",
        ),
        hospital_client=httpx.Client(
            transport=httpx.MockTransport(handler),
            base_url="http://hospital",
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        validator.ensure_hospital_exists(2, missing_detail="Hospital not found")

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Reference validation service is unavailable"
    validator.close()
