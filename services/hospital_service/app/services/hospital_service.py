from fastapi import HTTPException, status

from ..models.hospital import Hospital
from ..repositories.hospital_repository import HospitalRepository
from ..schemas.hospital import HospitalRequest, HospitalResponse


class HospitalService:
    CREATED_EVENT_TYPE = "hospital.created.v1"
    UPDATED_EVENT_TYPE = "hospital.updated.v1"
    DELETED_EVENT_TYPE = "hospital.deleted.v1"

    def __init__(self, repository: HospitalRepository) -> None:
        self.repository = repository

    def list_hospitals(self, offset: int, limit: int) -> list[HospitalResponse]:
        hospitals = self.repository.list_hospitals(offset, limit)
        return [self._to_response(hospital) for hospital in hospitals]

    def get_hospital(self, hospital_id: int) -> HospitalResponse:
        hospital = self.repository.get_hospital(hospital_id)
        if hospital is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")
        return self._to_response(hospital)

    def get_hospital_rooms(self, hospital_id: int) -> list[str]:
        hospital = self.repository.get_hospital(hospital_id)
        if hospital is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")
        return [room.name for room in hospital.rooms]

    def create_hospital(self, payload: HospitalRequest) -> HospitalResponse:
        rooms = self._normalize_rooms(payload.rooms)
        hospital = self.repository.create_hospital(
            name=payload.name,
            address=payload.address,
            contact_phone=payload.contact_phone,
            rooms=rooms,
            event_type=self.CREATED_EVENT_TYPE,
            routing_key=self.CREATED_EVENT_TYPE,
        )
        return self._to_response(hospital)

    def update_hospital(self, hospital_id: int, payload: HospitalRequest) -> HospitalResponse:
        hospital = self.repository.get_hospital(hospital_id)
        if hospital is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")
        rooms = self._normalize_rooms(payload.rooms)
        updated = self.repository.update_hospital(
            hospital,
            name=payload.name,
            address=payload.address,
            contact_phone=payload.contact_phone,
            rooms=rooms,
            event_type=self.UPDATED_EVENT_TYPE,
            routing_key=self.UPDATED_EVENT_TYPE,
        )
        return self._to_response(updated)

    def delete_hospital(self, hospital_id: int) -> None:
        hospital = self.repository.get_hospital(hospital_id)
        if hospital is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")
        self.repository.delete_hospital(
            hospital,
            event_type=self.DELETED_EVENT_TYPE,
            routing_key=self.DELETED_EVENT_TYPE,
        )

    def _normalize_rooms(self, rooms: list[str]) -> list[str]:
        normalized = [room.strip() for room in rooms if room.strip()]
        if not normalized:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="At least one room is required"
            )
        if len(set(normalized)) != len(normalized):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Room names must be unique"
            )
        return normalized

    def _to_response(self, hospital: Hospital) -> HospitalResponse:
        return HospitalResponse(
            id=hospital.id,
            name=hospital.name,
            address=hospital.address,
            contact_phone=hospital.contact_phone,
            rooms=[room.name for room in hospital.rooms],
        )
