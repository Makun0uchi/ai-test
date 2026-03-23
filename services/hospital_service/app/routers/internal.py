from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from ..core.dependencies import get_session, require_internal_token
from ..repositories.hospital_repository import HospitalRepository
from ..schemas.internal import InternalHospitalResponse, InternalHospitalRoomResponse
from ..services.hospital_service import HospitalService

router = APIRouter(prefix="/internal/hospitals", tags=["internal"])
InternalPrincipal = Annotated[None, Depends(require_internal_token)]


@router.get("/{hospital_id}", response_model=InternalHospitalResponse)
def get_hospital_reference(
    hospital_id: int,
    _: InternalPrincipal,
    session=Depends(get_session),
) -> InternalHospitalResponse:
    hospital = HospitalService(HospitalRepository(session)).get_hospital(hospital_id)
    return InternalHospitalResponse(id=hospital.id, name=hospital.name, rooms=hospital.rooms)


@router.get("/{hospital_id}/rooms/{room}", response_model=InternalHospitalRoomResponse)
def get_hospital_room_reference(
    hospital_id: int,
    room: str,
    _: InternalPrincipal,
    session=Depends(get_session),
) -> InternalHospitalRoomResponse:
    service = HospitalService(HospitalRepository(session))
    rooms = service.get_hospital_rooms(hospital_id)
    if room not in rooms:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital room not found")
    return InternalHospitalRoomResponse(hospital_id=hospital_id, room=room)
