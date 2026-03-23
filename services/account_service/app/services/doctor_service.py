from fastapi import HTTPException, status

from ..repositories.account_repository import AccountRepository
from ..schemas.account import AccountResponse


class DoctorService:
    def __init__(self, repository: AccountRepository) -> None:
        self.repository = repository

    def list_doctors(
        self, *, name_filter: str | None, offset: int, limit: int
    ) -> list[AccountResponse]:
        doctors = self.repository.list_doctors(name_filter=name_filter, offset=offset, limit=limit)
        return [
            AccountResponse(
                id=doctor.id,
                last_name=doctor.last_name,
                first_name=doctor.first_name,
                username=doctor.username,
                roles=sorted(role.name for role in doctor.roles),
            )
            for doctor in doctors
        ]

    def get_doctor(self, doctor_id: int) -> AccountResponse:
        doctor = self.repository.get_account_by_id(doctor_id)
        if doctor is None or "Doctor" not in {role.name for role in doctor.roles}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
        return AccountResponse(
            id=doctor.id,
            last_name=doctor.last_name,
            first_name=doctor.first_name,
            username=doctor.username,
            roles=sorted(role.name for role in doctor.roles),
        )
