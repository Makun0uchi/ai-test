from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Timetable(Base):
    __tablename__ = "timetables"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hospital_id: Mapped[int] = mapped_column(index=True)
    doctor_id: Mapped[int] = mapped_column(index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(), index=True)
    room: Mapped[str] = mapped_column(String(128), index=True)

    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="timetable",
        cascade="all, delete-orphan",
        order_by="Appointment.time",
    )


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        UniqueConstraint("timetable_id", "time", name="uq_timetable_appointment_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timetable_id: Mapped[int] = mapped_column(
        ForeignKey("timetables.id", ondelete="CASCADE"), index=True
    )
    patient_id: Mapped[int] = mapped_column(index=True)
    time: Mapped[datetime] = mapped_column(DateTime(), index=True)

    timetable: Mapped[Timetable] = relationship(back_populates="appointments")
