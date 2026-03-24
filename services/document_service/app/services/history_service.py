from datetime import datetime

from fastapi import HTTPException, status
from libs.service_common.reference_validation import ReferenceValidator

from ..core.security import AuthContext
from ..models.history import HistoryRecord
from ..repositories.history_repository import HistoryRepository
from ..schemas.history import HistoryRequest, HistoryResponse, HistorySearchResponse
from ..search.base import SearchGateway, SearchQuery


class HistoryService:
    CREATED_EVENT_TYPE = "history.created.v1"
    UPDATED_EVENT_TYPE = "history.updated.v1"

    def __init__(
        self,
        repository: HistoryRepository,
        search_gateway: SearchGateway,
        reference_validator: ReferenceValidator,
    ) -> None:
        self.repository = repository
        self.search_gateway = search_gateway
        self.reference_validator = reference_validator

    def list_by_patient(self, patient_id: int, principal: AuthContext) -> list[HistoryResponse]:
        self._ensure_history_access(patient_id, principal)
        items = self.repository.list_by_patient(patient_id)
        return [self._to_response(item) for item in items]

    def get_history(self, history_id: int, principal: AuthContext) -> HistoryResponse:
        history = self._require_history(history_id)
        self._ensure_history_access(history.patient_id, principal)
        return self._to_response(history)

    def create_history(self, payload: HistoryRequest, principal: AuthContext) -> HistoryResponse:
        self._ensure_editor(principal)
        self._validate_references(payload)
        history = self.repository.create_history(
            date=payload.date.replace(tzinfo=None),
            patient_id=payload.patient_id,
            hospital_id=payload.hospital_id,
            doctor_id=payload.doctor_id,
            room=payload.room,
            data=payload.data,
            event_type=self.CREATED_EVENT_TYPE,
            routing_key=self.CREATED_EVENT_TYPE,
        )
        return self._to_response(history)

    def update_history(
        self, history_id: int, payload: HistoryRequest, principal: AuthContext
    ) -> HistoryResponse:
        self._ensure_editor(principal)
        history = self._require_history(history_id)
        self._validate_references(payload)
        updated = self.repository.update_history(
            history,
            date=payload.date.replace(tzinfo=None),
            patient_id=payload.patient_id,
            hospital_id=payload.hospital_id,
            doctor_id=payload.doctor_id,
            room=payload.room,
            data=payload.data,
            event_type=self.UPDATED_EVENT_TYPE,
            routing_key=self.UPDATED_EVENT_TYPE,
        )
        return self._to_response(updated)

    def search(
        self,
        *,
        principal: AuthContext,
        query: str | None,
        patient_id: int | None,
        doctor_id: int | None,
        hospital_id: int | None,
        room: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        page: int,
        size: int,
    ) -> HistorySearchResponse:
        effective_patient_id = patient_id
        if "User" in principal.roles:
            effective_patient_id = principal.subject
        search_query = SearchQuery(
            query=query,
            patient_id=effective_patient_id,
            doctor_id=doctor_id,
            hospital_id=hospital_id,
            room=room,
            date_from=date_from.replace(tzinfo=None) if date_from else None,
            date_to=date_to.replace(tzinfo=None) if date_to else None,
            page=page,
            size=size,
        )
        total, ids = self.search_gateway.search(search_query)
        items: list[HistoryResponse] = []
        for history_id in ids:
            history = self.repository.get_history(history_id)
            if history is not None:
                if "User" in principal.roles and history.patient_id != principal.subject:
                    continue
                items.append(self._to_response(history))
        return HistorySearchResponse(total=total, items=items)

    def _require_history(self, history_id: int) -> HistoryRecord:
        history = self.repository.get_history(history_id)
        if history is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="History record not found"
            )
        return history

    def _ensure_history_access(self, patient_id: int, principal: AuthContext) -> None:
        elevated = {"Admin", "Manager", "Doctor"}
        if set(principal.roles).isdisjoint(elevated) and patient_id != principal.subject:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )

    def _ensure_editor(self, principal: AuthContext) -> None:
        elevated = {"Admin", "Manager", "Doctor"}
        if set(principal.roles).isdisjoint(elevated):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )

    def _validate_references(self, payload: HistoryRequest) -> None:
        self.reference_validator.ensure_account_has_role(
            payload.patient_id,
            role="User",
            missing_detail="Patient account not found",
            wrong_role_detail="Referenced account is not a patient",
        )
        self.reference_validator.ensure_account_has_role(
            payload.doctor_id,
            role="Doctor",
            missing_detail="Doctor account not found",
            wrong_role_detail="Referenced account is not a doctor",
        )
        self.reference_validator.ensure_hospital_exists(
            payload.hospital_id,
            missing_detail="Hospital not found",
        )
        self.reference_validator.ensure_hospital_room_exists(
            payload.hospital_id,
            payload.room,
            missing_detail="Hospital room not found",
        )

    def _to_response(self, history: HistoryRecord) -> HistoryResponse:
        return HistoryResponse(
            id=history.id,
            date=history.date,
            patient_id=history.patient_id,
            hospital_id=history.hospital_id,
            doctor_id=history.doctor_id,
            room=history.room,
            data=history.data,
        )
