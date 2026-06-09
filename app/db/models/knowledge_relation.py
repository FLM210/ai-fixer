"""知识库条目关联关系模型。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, get_schema_name
from app.db.compat import UUID as PgUUID


class KnowledgeRelation(Base):
    """知识条目之间的关联关系。"""

    __tablename__ = "knowledge_relations"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fixer.knowledge_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fixer.knowledge_entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    relation_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="related"
    )  # similar | supersedes | related
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    __table_args__ = (
        Index("ix_knowledge_relations_source", "source_id"),
        Index("ix_knowledge_relations_target", "target_id"),
        *([{"schema": "fixer"}] if get_schema_name() else []),
    )
