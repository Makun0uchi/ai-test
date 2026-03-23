from collections.abc import Sequence
from typing import Any, Protocol, cast
from urllib.parse import quote

import httpx
from fastapi import HTTPException, status


class ReferenceValidator(Protocol):
    def ensure_account_has_role(
        self,
        account_id: int,
        *,
        role: str,
        missing_detail: str,
        wrong_role_detail: str,
    ) -> None: ...

    def ensure_hospital_exists(self, hospital_id: int, *, missing_detail: str) -> None: ...

    def ensure_hospital_room_exists(
        self,
        hospital_id: int,
        room: str,
        *,
        missing_detail: str,
    ) -> None: ...

    def close(self) -> None: ...


class HttpReferenceValidator:
    def __init__(
        self,
        *,
        account_service_url: str,
        hospital_service_url: str,
        internal_api_key: str,
        account_client: httpx.Client | None = None,
        hospital_client: httpx.Client | None = None,
    ) -> None:
        headers = {"X-Internal-Token": internal_api_key}
        self._owns_account_client = account_client is None
        self._owns_hospital_client = hospital_client is None
        self.account_client = account_client or httpx.Client(
            base_url=account_service_url.rstrip("/"),
            headers=headers,
            timeout=5.0,
        )
        self.hospital_client = hospital_client or httpx.Client(
            base_url=hospital_service_url.rstrip("/"),
            headers=headers,
            timeout=5.0,
        )

    def ensure_account_has_role(
        self,
        account_id: int,
        *,
        role: str,
        missing_detail: str,
        wrong_role_detail: str,
    ) -> None:
        payload = self._get_json(
            self.account_client,
            f"/internal/accounts/{account_id}",
            missing_detail=missing_detail,
        )
        roles = payload.get("roles")
        if not isinstance(roles, Sequence) or role not in roles:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=wrong_role_detail)

    def ensure_hospital_exists(self, hospital_id: int, *, missing_detail: str) -> None:
        self._get_json(
            self.hospital_client,
            f"/internal/hospitals/{hospital_id}",
            missing_detail=missing_detail,
        )

    def ensure_hospital_room_exists(
        self,
        hospital_id: int,
        room: str,
        *,
        missing_detail: str,
    ) -> None:
        encoded_room = quote(room, safe="")
        self._get_json(
            self.hospital_client,
            f"/internal/hospitals/{hospital_id}/rooms/{encoded_room}",
            missing_detail=missing_detail,
        )

    def close(self) -> None:
        if self._owns_account_client:
            self.account_client.close()
        if self._owns_hospital_client:
            self.hospital_client.close()

    def _get_json(
        self,
        client: httpx.Client,
        path: str,
        *,
        missing_detail: str,
    ) -> dict[str, Any]:
        try:
            response = client.get(path)
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Reference validation service is unavailable",
            ) from exc

        if response.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=missing_detail)
        if response.status_code >= status.HTTP_400_BAD_REQUEST:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Reference validation service is unavailable",
            )

        return cast(dict[str, Any], response.json())
