"""生产环境上下文：用户预填充的环境信息，供 LLM 参考。"""

from datetime import datetime

from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EnvironmentContext(Base):
    """存储生产环境上下文信息（单行）。"""

    __tablename__ = "environment_context"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    updated_by: Mapped[str | None] = mapped_column(default="user")

    __table_args__ = ({"schema": "fixer"},)
