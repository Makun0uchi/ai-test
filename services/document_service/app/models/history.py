from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class HistoryRecord(Base):
    __tablename__ = "history_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[datetime] = mapped_column(DateTime(), index=True)
    patient_id: Mapped[int] = mapped_column(index=True)
    hospital_id: Mapped[int] = mapped_column(index=True)
    doctor_id: Mapped[int] = mapped_column(index=True)
    room: Mapped[str] = mapped_column(String(128), index=True)
    data: Mapped[str] = mapped_column(String(4000))
