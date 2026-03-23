from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Hospital(Base):
    __tablename__ = "hospitals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    address: Mapped[str] = mapped_column(String(512))
    contact_phone: Mapped[str] = mapped_column(String(64))

    rooms: Mapped[list["HospitalRoom"]] = relationship(
        back_populates="hospital",
        cascade="all, delete-orphan",
        order_by="HospitalRoom.id",
    )


class HospitalRoom(Base):
    __tablename__ = "hospital_rooms"
    __table_args__ = (UniqueConstraint("hospital_id", "name", name="uq_hospital_room_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hospital_id: Mapped[int] = mapped_column(ForeignKey("hospitals.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(128))

    hospital: Mapped[Hospital] = relationship(back_populates="rooms")
