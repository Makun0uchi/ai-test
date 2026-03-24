import json

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..models.hospital import Hospital, HospitalRoom
from .outbox_repository import HospitalOutboxRepository


class HospitalRepository:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.outbox_repository = HospitalOutboxRepository(session)

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
        event_type: str,
        routing_key: str,
    ) -> Hospital:
        hospital = Hospital(
            name=name,
            address=address,
            contact_phone=contact_phone,
            rooms=[HospitalRoom(name=room) for room in rooms],
        )
        self.session.add(hospital)
        self.session.flush()
        self.outbox_repository.create_event(
            hospital_id=hospital.id,
            event_type=event_type,
            routing_key=routing_key,
            payload=self._serialize_payload(hospital, event_type),
        )
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
        event_type: str,
        routing_key: str,
    ) -> Hospital:
        hospital.name = name
        hospital.address = address
        hospital.contact_phone = contact_phone
        hospital.rooms = [HospitalRoom(name=room) for room in rooms]
        self.session.add(hospital)
        self.session.flush()
        self.outbox_repository.create_event(
            hospital_id=hospital.id,
            event_type=event_type,
            routing_key=routing_key,
            payload=self._serialize_payload(hospital, event_type),
        )
        self.session.commit()
        self.session.refresh(hospital)
        return self.get_hospital(hospital.id) or hospital

    def delete_hospital(self, hospital: Hospital, *, event_type: str, routing_key: str) -> None:
        self.outbox_repository.create_event(
            hospital_id=hospital.id,
            event_type=event_type,
            routing_key=routing_key,
            payload=self._serialize_payload(hospital, event_type),
        )
        self.session.delete(hospital)
        self.session.commit()

    def _serialize_payload(self, hospital: Hospital, event_type: str) -> str:
        payload = {
            "eventType": event_type,
            "hospitalId": hospital.id,
            "hospital": {
                "id": hospital.id,
                "name": hospital.name,
                "address": hospital.address,
                "contactPhone": hospital.contact_phone,
                "rooms": [room.name for room in hospital.rooms],
            },
        }
        return json.dumps(payload, ensure_ascii=False)
