from fastapi import APIRouter, Depends, Query

from ..core.dependencies import get_account_repository, get_current_account
from ..models.account import Account
from ..repositories.account_repository import AccountRepository
from ..schemas.account import AccountResponse
from ..services.doctor_service import DoctorService

router = APIRouter(prefix="/api/Doctors", tags=["doctors"])


@router.get("", response_model=list[AccountResponse])
def list_doctors(
    _: Account = Depends(get_current_account),
    repository: AccountRepository = Depends(get_account_repository),
    name_filter: str | None = Query(default=None, alias="nameFilter"),
    from_: int = Query(default=0, alias="from", ge=0),
    count: int = Query(default=20, alias="count", ge=1, le=100),
) -> list[AccountResponse]:
    return DoctorService(repository).list_doctors(
        name_filter=name_filter, offset=from_, limit=count
    )


@router.get("/{doctor_id}", response_model=AccountResponse)
def get_doctor(
    doctor_id: int,
    _: Account = Depends(get_current_account),
    repository: AccountRepository = Depends(get_account_repository),
) -> AccountResponse:
    return DoctorService(repository).get_doctor(doctor_id)
