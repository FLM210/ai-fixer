"""公共工作流运行逻辑, 同时被 WebSocket 和 HTTP 回调两种模式使用。"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def load_env_context() -> str | None:
    """从数据库加载生产环境上下文。"""
    try:
        from sqlalchemy import select

        from app.db import session_scope
        from app.db.models.environment_context import EnvironmentContext

        async with session_scope() as session:
            stmt = select(EnvironmentContext).where(EnvironmentContext.id == 1)
            result = await session.execute(stmt)
            ctx = result.scalar_one_or_none()
            if ctx and ctx.content.strip():
                return ctx.content
    except Exception:
        logger.warning("加载环境上下文失败", exc_info=True)
    return None


def build_initial_state(
    incident_id: str,
    thread_id: str,
    alert_text: str,
    chat_id: str,
    message_id: str,
    sender_id: str,
    env_context: str | None = None,
) -> dict[str, Any]:
    """构建 LangGraph 工作流的初始状态。"""
    from uuid import uuid4

    return {
        "incident_id": incident_id,
        "trace_id": str(uuid4()),
        "raw_alert": alert_text,
        "source_meta": {
            "chat_id": chat_id,
            "msg_id": message_id,
            "sender": sender_id,
        },
        "category": None,
        "severity": None,
        "service": None,
        "is_duplicate": False,
        "diagnosis_messages": [],
        "evidence": {},
        "diagnosis_summary": None,
        "confidence": None,
        "similar_incidents": [],
        "proposals": [],
        "policy_decisions": [],
        "approval_decisions": {},
        "awaiting_since": None,
        "diagnosis_approved": None,
        "diagnosis_confirmed": None,
        "proposals_approved": None,
        "proposal_confirmed": None,
        "execution_results": [],
        "env_context": env_context,
        "llm_turns": [],
        "llm_cost_tokens": 0,
        "final_status": None,
    }


async def send_workflow_result(chat_id: str, result: dict[str, Any]) -> None:
    """发送工作流最终结果到飞书群。"""
    from app.lark.card_sender import send_result_card

    incident_id = result.get("incident_id", "unknown")
    diagnosis = result.get("diagnosis_summary", "无诊断结果")
    execution_results = result.get("execution_results", [])
    final_status = result.get("final_status") or "unknown"
    auto_resolved = final_status == "resolved"

    results_dicts = [
        {
            "plugin_name": r.get("plugin_name", "unknown"),
            "status": r.get("status", "unknown"),
            "error": r.get("error"),
        }
        for r in execution_results
    ]

    try:
        await send_result_card(
            chat_id=chat_id,
            incident_id=incident_id,
            diagnosis=diagnosis or "无诊断结果",
            execution_results=results_dicts,
            auto_resolved=auto_resolved,
        )
        logger.info(
            "工作流结果已发送: incident=%s status=%s", incident_id, final_status
        )
    except Exception:
        logger.exception("发送工作流结果失败: incident=%s", incident_id)


async def save_workflow_result(result: dict[str, Any]) -> None:
    """保存工作流结果 (含 LLM 对话) 到数据库。"""
    from sqlalchemy import select

    from app.db import session_scope
    from app.db.models.diagnosis import Diagnosis
    from app.db.models.fix_proposal import FixProposal
    from app.db.models.incident import Incident
    from app.db.models.llm_turn import LLMTurn

    try:
        async with session_scope() as session:
            incident_id = result.get("incident_id")

            existing_result = await session.execute(
                select(Incident).where(Incident.id == str(incident_id))
            )
            existing = existing_result.scalar_one_or_none()

            if existing:
                existing.status = result.get("final_status") or existing.status
                existing.category = result.get("category") or existing.category
                existing.service = result.get("service") or existing.service
                existing.severity = result.get("severity") or existing.severity
                existing.summary = (
                    result.get("diagnosis_summary") or existing.summary or ""
                )[:1024]
                existing.llm_cost_tokens = result.get("llm_cost_tokens", 0)
                incident = existing
            else:
                incident = Incident(
                    id=incident_id,
                    fingerprint=result.get("raw_alert", "")[:64],
                    status=result.get("final_status") or "completed",
                    category=result.get("category"),
                    service=result.get("service"),
                    severity=result.get("severity"),
                    summary=(result.get("diagnosis_summary") or "")[:1024],
                    raw_alert={"text": result.get("raw_alert", "")},
                    chat_id=result.get("source_meta", {}).get("chat_id"),
                    source_message_id=result.get("source_meta", {}).get("msg_id"),
                    llm_cost_tokens=result.get("llm_cost_tokens", 0),
                )
                session.add(incident)

            if result.get("diagnosis_summary"):
                diagnosis = Diagnosis(
                    incident_id=incident.id,
                    root_cause=result["diagnosis_summary"][:2048],
                    confidence=result.get("confidence", 0),
                    evidence=[result.get("evidence", {})],
                )
                session.add(diagnosis)

            for p in result.get("proposals", []):
                proposal = FixProposal(
                    incident_id=incident.id,
                    plugin_name=p.get("plugin_name", ""),
                    args=p.get("args", {}),
                    risk_level=p.get("risk_level", "medium"),
                    description=p.get("description", ""),
                    expected_outcome=p.get("expected_outcome"),
                    source=p.get("source", "plugin"),
                )
                session.add(proposal)

            for t in result.get("llm_turns", []):
                turn = LLMTurn(
                    incident_id=incident.id,
                    phase=t.get("phase", ""),
                    turn_index=t.get("turn_index", 0),
                    role=t.get("role", ""),
                    content=str(t.get("content", ""))[:10000],
                    tool_name=t.get("tool_name"),
                    tool_input=t.get("tool_input"),
                )
                session.add(turn)

            await session.flush()
            logger.info(
                "工作流结果已保存: incident=%s, llm_turns=%d",
                incident.id,
                len(result.get("llm_turns", [])),
            )

    except Exception:
        logger.exception("保存工作流结果失败")


async def create_checkpointer() -> Any:
    """根据环境创建 checkpointer: 生产用 PostgreSQL, 开发用内存。"""
    try:
        from app.config import get_settings

        settings = get_settings()
        database_url = settings.database_url

        # 如果配置了数据库, 使用 PostgreSQL 持久化
        if database_url and "postgresql" in database_url:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            from psycopg.rows import dict_row
            from psycopg_pool import AsyncConnectionPool

            pool = AsyncConnectionPool(
                database_url, kwargs={"row_factory": dict_row}
            )
            checkpointer = AsyncPostgresSaver(conn=pool)
            await checkpointer.setup()
            logger.info("使用 PostgreSQL checkpointer (生产模式)")
            return checkpointer
    except Exception:
        logger.warning("PostgreSQL checkpointer 初始化失败, 回退到内存模式", exc_info=True)

    # 开发模式: 使用内存 checkpointer
    from langgraph.checkpoint.memory import MemorySaver

    logger.info("使用 MemorySaver checkpointer (开发模式)")
    return MemorySaver()
