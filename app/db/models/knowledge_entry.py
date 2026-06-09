"""知识库条目模型。

支持三种来源：手动手册(manual)、incident 自动提取(incident)、外部 runbook(runbook)。
包含版本历史和过期机制。
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, get_schema_name
from app.db.compat import UUID as PgUUID
from app.db.compat import JSONCompat as JSONB


class KnowledgeEntry(Base):
    """知识库条目主表。"""

    __tablename__ = "knowledge_entries"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), index=True)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    source_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="manual"
    )  # manual | incident | runbook
    source_incident_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fixer.incidents.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="published", index=True
    )  # draft | published | archived | review
    created_by: Mapped[str | None] = mapped_column(String(64))
    current_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_knowledge_entries_source_type", "source_type"),
        Index("ix_knowledge_entries_status_created", "status", "created_at"),
        *([{"schema": "fixer"}] if get_schema_name() else []),
    )
