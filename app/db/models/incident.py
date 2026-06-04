from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models._enums import IncidentStatus, ResolutionType


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=IncidentStatus.NEW)
    category: Mapped[str | None] = mapped_column(String(64))
    service: Mapped[str | None] = mapped_column(String(128))
    namespace: Mapped[str | None] = mapped_column(String(64))
    severity: Mapped[str | None] = mapped_column(String(16))
    summary: Mapped[str | None] = mapped_column(String(1024))
    raw_alert: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    chat_id: Mapped[str | None] = mapped_column(String(128))
    source_message_id: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_type: Mapped[str | None] = mapped_column(String(32))  # auto/manual/escalated
    resolution_time_seconds: Mapped[int | None] = mapped_column()
    llm_cost_tokens: Mapped[int | None] = mapped_column(default=0)

    __table_args__ = (
        Index("ix_incidents_fingerprint_created", "fingerprint", "created_at"),
        Index("ix_incidents_status", "status"),
        {"schema": "fixer"},
    )
