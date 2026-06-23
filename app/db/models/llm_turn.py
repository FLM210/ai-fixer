"""LLM 对话轮次模型：记录与 LLM 的每一轮交互。"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, get_table_args
from app.db.compat import UUID as PgUUID
from app.db.compat import JSONCompat as JSONB


class LLMTurn(Base):
    """记录 LLM agent loop 的每一轮对话。"""

    __tablename__ = "llm_turns"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    incident_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("fixer.incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phase: Mapped[str] = mapped_column(String(32), nullable=False)  # triage | diagnose | propose
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # user | assistant | tool | system
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tool_name: Mapped[str | None] = mapped_column(String(128))
    tool_input: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    tool_output: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    __table_args__ = get_table_args()
