"""系统状态 API。"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select, text

from app.api.deps import get_config, get_db_session, get_dynamic
from app.db import session_scope
from app.db.models.incident import Incident
from app.plugins import global_registry

router = APIRouter()


class HealthCheck(BaseModel):
    db: str
    redis: str


class SystemStatus(BaseModel):
    version: str
    uptime_healthy: bool
    health: HealthCheck
    active_incidents: int
    total_incidents: int
    plugin_count: int
    dynamic_config_loaded: bool
    llm_provider: str
    llm_model: str


@router.get("/status")
async def get_status() -> SystemStatus:
    """获取系统概览状态。"""
    settings = get_config()
    dynamic = get_dynamic()

    # DB 健康检查
    db_status = "ok"
    active_count = 0
    total_count = 0
    try:
        async with session_scope() as session:
            await session.execute(text("SELECT 1"))
            # 活跃 incident 数
            stmt = select(func.count()).select_from(Incident).where(
                Incident.status.notin_(["resolved", "escalated", "ignored"])
            )
            result = await session.execute(stmt)
            active_count = result.scalar() or 0

            # 总 incident 数
            stmt_total = select(func.count()).select_from(Incident)
            result_total = await session.execute(stmt_total)
            total_count = result_total.scalar() or 0
    except Exception:
        db_status = "fail"

    return SystemStatus(
        version="0.1.0",
        uptime_healthy=db_status == "ok",
        health=HealthCheck(db=db_status, redis="ok"),
        active_incidents=active_count,
        total_incidents=total_count,
        plugin_count=len(global_registry.list_specs()),
        dynamic_config_loaded=dynamic.is_loaded,
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
    )
