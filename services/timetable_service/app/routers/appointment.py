from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from ..core.dependencies import get_current_principal, get_session
from ..core.security import AuthContext
from ..repositories.timetable_repository import TimetableRepository
from ..services.timetable_service import TimetableService

router = APIRouter(prefix="/api/Appointment", tags=["appointment"])
AnyPrincipal = Annotated[AuthContext, Depends(get_current_principal)]


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment(
    appointment_id: int,
    principal: AnyPrincipal,
    session: Session = Depends(get_session),
) -> Response:
    TimetableService(TimetableRepository(session)).delete_appointment(appointment_id, principal)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
