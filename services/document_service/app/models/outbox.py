from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class HistoryIndexOutbox(Base):
    __tablename__ = "history_index_outbox"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    history_id: Mapped[int] = mapped_column(index=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    routing_key: Mapped[str] = mapped_column(String(255), index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), default=None, index=True)
    payload: Mapped[str] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True, index=True)
