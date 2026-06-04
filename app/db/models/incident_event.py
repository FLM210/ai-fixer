from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from app.db.compat import JSONCompat as JSONB
from app.db.compat import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, get_table_args


class IncidentEvent(Base):
    __tablename__ = "incident_events"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    incident_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fixer.incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    actor: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = get_table_args()
