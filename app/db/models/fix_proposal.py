from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import text,  DateTime, ForeignKey, String, func
from app.db.compat import JSONCompat as JSONB
from app.db.compat import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, get_table_args


class FixProposal(Base):
    __tablename__ = "fix_proposals"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    incident_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fixer.incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plugin_name: Mapped[str] = mapped_column(String(128), nullable=False)
    args: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(String(2048), nullable=False)
    expected_outcome: Mapped[str | None] = mapped_column(String(2048))
    rollback_hint: Mapped[str | None] = mapped_column(String(2048))
    source: Mapped[str] = mapped_column(String(32), nullable=False)  # plugin | llm_fallback
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    __table_args__ = get_table_args()
