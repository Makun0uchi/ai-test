from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from ..core.dependencies import get_current_principal, get_session, require_roles
from ..core.security import AuthContext
from ..repositories.hospital_repository import HospitalRepository
from ..schemas.hospital import HospitalRequest, HospitalResponse
from ..services.hospital_service import HospitalService

router = APIRouter(prefix="/api/Hospitals", tags=["hospitals"])
ManagerPrincipal = Annotated[AuthContext, Depends(require_roles("Admin", "Manager"))]


@router.get("", response_model=list[HospitalResponse])
def list_hospitals(
    _: AuthContext = Depends(get_current_principal),
    session=Depends(get_session),
    from_: int = Query(default=0, alias="from", ge=0),
    count: int = Query(default=20, alias="count", ge=1, le=100),
) -> list[HospitalResponse]:
    repository = HospitalRepository(session)
    return HospitalService(repository).list_hospitals(from_, count)


@router.get("/{hospital_id}", response_model=HospitalResponse)
def get_hospital(
    hospital_id: int,
    _: AuthContext = Depends(get_current_principal),
    session=Depends(get_session),
) -> HospitalResponse:
    repository = HospitalRepository(session)
    return HospitalService(repository).get_hospital(hospital_id)


@router.get("/{hospital_id}/Rooms", response_model=list[str])
def get_hospital_rooms(
    hospital_id: int,
    _: AuthContext = Depends(get_current_principal),
    session=Depends(get_session),
) -> list[str]:
    repository = HospitalRepository(session)
    return HospitalService(repository).get_hospital_rooms(hospital_id)


@router.post("", response_model=HospitalResponse, status_code=status.HTTP_201_CREATED)
def create_hospital(
    payload: HospitalRequest,
    _: ManagerPrincipal,
    session=Depends(get_session),
) -> HospitalResponse:
    repository = HospitalRepository(session)
    return HospitalService(repository).create_hospital(payload)


@router.put("/{hospital_id}", response_model=HospitalResponse)
def update_hospital(
    hospital_id: int,
    payload: HospitalRequest,
    _: ManagerPrincipal,
    session=Depends(get_session),
) -> HospitalResponse:
    repository = HospitalRepository(session)
    return HospitalService(repository).update_hospital(hospital_id, payload)


@router.delete("/{hospital_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hospital(
    hospital_id: int,
    _: ManagerPrincipal,
    session=Depends(get_session),
) -> Response:
    repository = HospitalRepository(session)
    HospitalService(repository).delete_hospital(hospital_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
