from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import text,  DateTime, ForeignKey, Integer, String, func
from app.db.compat import JSONCompat as JSONB
from app.db.compat import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, get_table_args


class DiagnosticPath(Base):
    """记录 LLM agent loop 的工具调用序列和每步耗时，用于诊断路径优化。"""
    __tablename__ = "diagnostic_paths"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    incident_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fixer.incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    plugin_name: Mapped[str] = mapped_column(String(128), nullable=False)
    args: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    output_summary: Mapped[str | None] = mapped_column(String(2048))
    evidence_produced: Mapped[bool] = mapped_column(default=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    tokens_used: Mapped[int | None] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    __table_args__ = get_table_args()
