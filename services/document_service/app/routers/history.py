from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from libs.service_common.reference_validation import ReferenceValidator
from sqlalchemy.orm import Session

from ..core.dependencies import (
    get_current_principal,
    get_reference_validator,
    get_search_gateway,
    get_session,
)
from ..core.security import AuthContext
from ..repositories.history_repository import HistoryRepository
from ..schemas.history import HistoryRequest, HistoryResponse, HistorySearchResponse
from ..search.base import SearchGateway
from ..services.history_service import HistoryService

router = APIRouter(prefix="/api/History", tags=["history"])


def _service(
    session: Session,
    search_gateway: SearchGateway,
    reference_validator: ReferenceValidator,
) -> HistoryService:
    return HistoryService(HistoryRepository(session), search_gateway, reference_validator)


@router.get("/Search", response_model=HistorySearchResponse)
def search_history(
    principal: AuthContext = Depends(get_current_principal),
    session: Session = Depends(get_session),
    search_gateway: SearchGateway = Depends(get_search_gateway),
    reference_validator: ReferenceValidator = Depends(get_reference_validator),
    query: str | None = Query(default=None),
    patient_id: int | None = Query(default=None, alias="patientId"),
    doctor_id: int | None = Query(default=None, alias="doctorId"),
    hospital_id: int | None = Query(default=None, alias="hospitalId"),
    room: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None, alias="dateFrom"),
    date_to: datetime | None = Query(default=None, alias="dateTo"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> HistorySearchResponse:
    return _service(session, search_gateway, reference_validator).search(
        principal=principal,
        query=query,
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        room=room,
        date_from=date_from,
        date_to=date_to,
        page=page,
        size=size,
    )


@router.get("/Account/{patient_id}", response_model=list[HistoryResponse])
def list_patient_history(
    patient_id: int,
    principal: AuthContext = Depends(get_current_principal),
    session: Session = Depends(get_session),
    search_gateway: SearchGateway = Depends(get_search_gateway),
    reference_validator: ReferenceValidator = Depends(get_reference_validator),
) -> list[HistoryResponse]:
    return _service(session, search_gateway, reference_validator).list_by_patient(
        patient_id, principal
    )


@router.get("/{history_id}", response_model=HistoryResponse)
def get_history(
    history_id: int,
    principal: AuthContext = Depends(get_current_principal),
    session: Session = Depends(get_session),
    search_gateway: SearchGateway = Depends(get_search_gateway),
    reference_validator: ReferenceValidator = Depends(get_reference_validator),
) -> HistoryResponse:
    return _service(session, search_gateway, reference_validator).get_history(history_id, principal)


@router.post("", response_model=HistoryResponse, status_code=status.HTTP_201_CREATED)
def create_history(
    payload: HistoryRequest,
    principal: AuthContext = Depends(get_current_principal),
    session: Session = Depends(get_session),
    search_gateway: SearchGateway = Depends(get_search_gateway),
    reference_validator: ReferenceValidator = Depends(get_reference_validator),
) -> HistoryResponse:
    return _service(session, search_gateway, reference_validator).create_history(payload, principal)


@router.put("/{history_id}", response_model=HistoryResponse)
def update_history(
    history_id: int,
    payload: HistoryRequest,
    principal: AuthContext = Depends(get_current_principal),
    session: Session = Depends(get_session),
    search_gateway: SearchGateway = Depends(get_search_gateway),
    reference_validator: ReferenceValidator = Depends(get_reference_validator),
) -> HistoryResponse:
    return _service(session, search_gateway, reference_validator).update_history(
        history_id, payload, principal
    )
