"""生产环境上下文 API。"""

from __future__ import annotations

from datetime import UTC

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.db.models.environment_context import EnvironmentContext

router = APIRouter()


class EnvironmentContextResponse(BaseModel):
    content: str
    updated_at: str | None = None
    updated_by: str | None = None


class EnvironmentContextUpdateRequest(BaseModel):
    content: str
    updated_by: str = "user"


@router.get("/environment-context")
async def get_environment_context(
    session: AsyncSession = Depends(get_db_session),
) -> EnvironmentContextResponse:
    """获取生产环境上下文。"""
    stmt = select(EnvironmentContext).where(EnvironmentContext.id == 1)
    result = await session.execute(stmt)
    ctx = result.scalar_one_or_none()

    if not ctx:
        return EnvironmentContextResponse(content="")

    return EnvironmentContextResponse(
        content=ctx.content,
        updated_at=ctx.updated_at.isoformat() if ctx.updated_at else None,
        updated_by=ctx.updated_by,
    )


@router.put("/environment-context")
async def update_environment_context(
    request: EnvironmentContextUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> EnvironmentContextResponse:
    """更新生产环境上下文。"""
    from datetime import datetime

    stmt = select(EnvironmentContext).where(EnvironmentContext.id == 1)
    result = await session.execute(stmt)
    ctx = result.scalar_one_or_none()

    if ctx:
        ctx.content = request.content
        ctx.updated_by = request.updated_by
        ctx.updated_at = datetime.now(UTC)
    else:
        ctx = EnvironmentContext(
            id=1,
            content=request.content,
            updated_by=request.updated_by,
        )
        session.add(ctx)

    await session.flush()

    return EnvironmentContextResponse(
        content=ctx.content,
        updated_at=ctx.updated_at.isoformat() if ctx.updated_at else None,
        updated_by=ctx.updated_by,
    )
