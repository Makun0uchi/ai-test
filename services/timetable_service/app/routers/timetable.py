from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from ..core.dependencies import get_current_principal, get_session, require_roles
from ..core.security import AuthContext
from ..repositories.timetable_repository import TimetableRepository
from ..schemas.timetable import (
    AppointmentRequest,
    AppointmentResponse,
    TimetableRequest,
    TimetableResponse,
)
from ..services.timetable_service import TimetableService

router = APIRouter(prefix="/api/Timetable", tags=["timetable"])
ManagerPrincipal = Annotated[AuthContext, Depends(require_roles("Admin", "Manager"))]
UserPrincipal = Annotated[AuthContext, Depends(require_roles("User"))]


def _service(session: Session) -> TimetableService:
    return TimetableService(TimetableRepository(session))


@router.post("", response_model=TimetableResponse, status_code=status.HTTP_201_CREATED)
def create_timetable(
    payload: TimetableRequest,
    _: ManagerPrincipal,
    session: Session = Depends(get_session),
) -> TimetableResponse:
    return _service(session).create_timetable(payload)


@router.put("/{timetable_id}", response_model=TimetableResponse)
def update_timetable(
    timetable_id: int,
    payload: TimetableRequest,
    _: ManagerPrincipal,
    session: Session = Depends(get_session),
) -> TimetableResponse:
    return _service(session).update_timetable(timetable_id, payload)


@router.delete("/{timetable_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_timetable(
    timetable_id: int,
    _: ManagerPrincipal,
    session: Session = Depends(get_session),
) -> Response:
    _service(session).delete_timetable(timetable_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/Doctor/{doctor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_doctor_timetables(
    doctor_id: int,
    _: ManagerPrincipal,
    session: Session = Depends(get_session),
) -> Response:
    _service(session).delete_by_doctor(doctor_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/Hospital/{hospital_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hospital_timetables(
    hospital_id: int,
    _: ManagerPrincipal,
    session: Session = Depends(get_session),
) -> Response:
    _service(session).delete_by_hospital(hospital_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/Hospital/{hospital_id}", response_model=list[TimetableResponse])
def list_hospital_timetables(
    hospital_id: int,
    _: AuthContext = Depends(get_current_principal),
    session: Session = Depends(get_session),
    from_: datetime = Query(alias="from"),
    to: datetime = Query(alias="to"),
) -> list[TimetableResponse]:
    return _service(session).list_by_hospital(hospital_id, from_, to)


@router.get("/Doctor/{doctor_id}", response_model=list[TimetableResponse])
def list_doctor_timetables(
    doctor_id: int,
    _: AuthContext = Depends(get_current_principal),
    session: Session = Depends(get_session),
    from_: datetime = Query(alias="from"),
    to: datetime = Query(alias="to"),
) -> list[TimetableResponse]:
    return _service(session).list_by_doctor(doctor_id, from_, to)


@router.get("/Hospital/{hospital_id}/Room/{room}", response_model=list[TimetableResponse])
def list_room_timetables(
    hospital_id: int,
    room: str,
    _: AuthContext = Depends(get_current_principal),
    session: Session = Depends(get_session),
    from_: datetime = Query(alias="from"),
    to: datetime = Query(alias="to"),
) -> list[TimetableResponse]:
    return _service(session).list_by_hospital_room(hospital_id, room, from_, to)


@router.get("/{timetable_id}/Appointments", response_model=list[datetime])
def list_available_appointments(
    timetable_id: int,
    _: AuthContext = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> list[datetime]:
    return _service(session).list_available_appointments(timetable_id)


@router.post(
    "/{timetable_id}/Appointments",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_appointment(
    timetable_id: int,
    payload: AppointmentRequest,
    principal: UserPrincipal,
    session: Session = Depends(get_session),
) -> AppointmentResponse:
    return _service(session).create_appointment(timetable_id, payload, principal)
