"""知识库条目版本历史模型。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, get_schema_name
from app.db.compat import UUID as PgUUID
from app.db.compat import JSONCompat as JSONB


class KnowledgeRevision(Base):
    """知识条目的版本历史记录。每次编辑自动创建一个 revision。"""

    __tablename__ = "knowledge_revisions"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    entry_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fixer.knowledge_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(64))
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    change_summary: Mapped[str | None] = mapped_column(String(512))
    created_by: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    __table_args__ = (
        Index(
            "ix_knowledge_revisions_entry_rev",
            "entry_id",
            "revision_number",
            unique=True,
        ),
        *([{"schema": "fixer"}] if get_schema_name() else []),
    )
