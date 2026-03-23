from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..models.hospital import Hospital, HospitalRoom


class HospitalRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_hospitals(self, offset: int, limit: int) -> list[Hospital]:
        statement = (
            select(Hospital)
            .options(joinedload(Hospital.rooms))
            .order_by(Hospital.id)
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(statement).unique())

    def get_hospital(self, hospital_id: int) -> Hospital | None:
        statement = (
            select(Hospital).options(joinedload(Hospital.rooms)).where(Hospital.id == hospital_id)
        )
        return self.session.scalar(statement)

    def create_hospital(
        self,
        *,
        name: str,
        address: str,
        contact_phone: str,
        rooms: list[str],
    ) -> Hospital:
        hospital = Hospital(
            name=name,
            address=address,
            contact_phone=contact_phone,
            rooms=[HospitalRoom(name=room) for room in rooms],
        )
        self.session.add(hospital)
        self.session.commit()
        self.session.refresh(hospital)
        return self.get_hospital(hospital.id) or hospital

    def update_hospital(
        self,
        hospital: Hospital,
        *,
        name: str,
        address: str,
        contact_phone: str,
        rooms: list[str],
    ) -> Hospital:
        hospital.name = name
        hospital.address = address
        hospital.contact_phone = contact_phone
        hospital.rooms = [HospitalRoom(name=room) for room in rooms]
        self.session.add(hospital)
        self.session.commit()
        self.session.refresh(hospital)
        return self.get_hospital(hospital.id) or hospital

    def delete_hospital(self, hospital: Hospital) -> None:
        self.session.delete(hospital)
        self.session.commit()
