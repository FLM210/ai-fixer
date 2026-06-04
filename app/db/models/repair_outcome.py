from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import text,  DateTime, ForeignKey, Integer, String, func
from app.db.compat import JSONCompat as JSONB
from app.db.compat import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, get_table_args


class RepairOutcome(Base):
    """记录每次修复的 before/after 指标对比，用于学习反馈。"""
    __tablename__ = "repair_outcomes"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    incident_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fixer.incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    execution_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fixer.fix_executions.id", ondelete="CASCADE"),
        nullable=False,
    )
    plugin_name: Mapped[str] = mapped_column(String(128), nullable=False)
    success: Mapped[bool] = mapped_column(nullable=False)
    metrics_before: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    metrics_after: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    verified: Mapped[bool] = mapped_column(default=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    __table_args__ = get_table_args()
