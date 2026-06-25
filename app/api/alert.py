"""告警接收 API：接收告警消息，触发 LLM 工作流，返回完整处理结果。"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.db import session_scope
from app.db.models.diagnosis import Diagnosis
from app.db.models.fix_proposal import FixProposal
from app.db.models.incident import Incident
from app.graph.state import GraphState
from app.graph.workflow import create_workflow

router = APIRouter()
logger = logging.getLogger(__name__)


class AlertRequest(BaseModel):
    text: str
    source: str = "api"
    chat_id: str = ""


class TriageResult(BaseModel):
    category: str | None = None
    severity: str | None = None
    service: str | None = None


class DiagnosisResult(BaseModel):
    summary: str | None = None
    confidence: float | None = None
    evidence: dict[str, Any] = {}
    similar_incidents: list[dict[str, Any]] = []


class ProposalResult(BaseModel):
    plugin_name: str
    description: str | None = None
    risk_level: str | None = None
    expected_outcome: str | None = None
    args: dict[str, Any] = {}


class LLMTurnResult(BaseModel):
    phase: str
    turn_index: int
    role: str
    content: str
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None


class AlertResponse(BaseModel):
    incident_id: str
    status: str
    triage: TriageResult
    diagnosis: DiagnosisResult
    proposals: list[ProposalResult]
    llm_turns: list[LLMTurnResult] = []
    execution_results: list[dict[str, Any]] = []
    raw_workflow_state: dict[str, Any] = {}


@router.post("/alert")
async def receive_alert(request: AlertRequest) -> AlertResponse:
    """接收告警，触发完整 LLM 工作流，返回处理结果。"""
    incident_id = str(uuid4())
    trace_id = str(uuid4())

    logger.info("收到告警: incident=%s text=%s", incident_id, request.text[:100])

    # 加载环境上下文
    env_context = None
    try:
        async with session_scope() as session:
            from app.db.models.environment_context import EnvironmentContext

            stmt = select(EnvironmentContext).where(EnvironmentContext.id == 1)
            result = await session.execute(stmt)
            ctx = result.scalar_one_or_none()
            if ctx and ctx.content.strip():
                env_context = ctx.content
    except Exception:
        logger.warning("加载环境上下文失败", exc_info=True)

    # 构建初始状态
    initial_state: GraphState = {
        "incident_id": incident_id,
        "trace_id": trace_id,
        "raw_alert": request.text,
        "source_meta": {"source": request.source, "chat_id": request.chat_id},
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
        "proposals_approved": None,
        "execution_results": [],
        "env_context": env_context,
        "llm_turns": [],
        "llm_cost_tokens": 0,
        "final_status": None,
    }

    # 执行工作流（使用 checkpointer 支持 interrupt/resume）
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.errors import GraphInterrupt

    checkpointer = MemorySaver()
    config = {"configurable": {"thread_id": str(uuid4())}}
    workflow = create_workflow()
    app = workflow.compile(checkpointer=checkpointer)

    try:
        result = await asyncio.wait_for(
            app.ainvoke(initial_state, config=config),
            timeout=300,
        )

        # 检查是否被 interrupt 暂停（LangGraph 通过 __interrupt__ 字段标识）
        if isinstance(result, dict) and "__interrupt__" in result:
            interrupt_type = "unknown"
            interrupts = result.get("__interrupt__", [])
            if interrupts and hasattr(interrupts[0], "value"):
                interrupt_data = interrupts[0].value
                if isinstance(interrupt_data, dict):
                    interrupt_type = interrupt_data.get("type", "unknown")

            logger.info(
                "工作流暂停等待确认: incident=%s type=%s",
                incident_id, interrupt_type,
            )

            # 注册到 workflow_manager 以便飞书卡片回调可以 resume
            if request.chat_id:
                from app.lark.workflow_manager import workflow_manager

                workflow_manager.register_pending(
                    thread_id=config["configurable"]["thread_id"],
                    incident_id=incident_id,
                    chat_id=request.chat_id,
                    interrupt_type=interrupt_type,
                    app=app,
                    config=config,
                )

            return AlertResponse(
                incident_id=incident_id,
                status="awaiting_approval",
                triage=TriageResult(
                    category=result.get("category"),
                    severity=result.get("severity"),
                    service=result.get("service"),
                ),
                diagnosis=DiagnosisResult(
                    summary=result.get("diagnosis_summary") or "诊断完成，等待用户确认",
                    confidence=result.get("confidence"),
                ),
                proposals=[],
                llm_turns=[
                    LLMTurnResult(
                        phase=t.get("phase", ""),
                        turn_index=t.get("turn_index", 0),
                        role=t.get("role", ""),
                        content=str(t.get("content", "")),
                        tool_name=t.get("tool_name"),
                        tool_input=t.get("tool_input"),
                    )
                    for t in result.get("llm_turns", [])
                ],
            )

    except GraphInterrupt as e:
        # 兼容旧版 LangGraph：GraphInterrupt 也可能直接抛出
        logger.info("GraphInterrupt caught: type=%s", type(e).__name__)
        interrupt_type = "unknown"
        if e.interrupts:
            interrupt_data = e.interrupts[0].value
            if isinstance(interrupt_data, dict):
                interrupt_type = interrupt_data.get("type", "unknown")

        logger.info(
            "工作流暂停等待确认: incident=%s type=%s", incident_id, interrupt_type
        )

        if request.chat_id:
            from app.lark.workflow_manager import workflow_manager

            workflow_manager.register_pending(
                thread_id=config["configurable"]["thread_id"],
                incident_id=incident_id,
                chat_id=request.chat_id,
                interrupt_type=interrupt_type,
                app=app,
                config=config,
            )

        return AlertResponse(
            incident_id=incident_id,
            status="awaiting_approval",
            triage=TriageResult(),
            diagnosis=DiagnosisResult(summary="诊断完成，等待用户确认"),
            proposals=[],
        )
    except TimeoutError:
        logger.error("工作流超时: incident=%s", incident_id)
        return AlertResponse(
            incident_id=incident_id,
            status="timeout",
            triage=TriageResult(),
            diagnosis=DiagnosisResult(summary="工作流执行超时"),
            proposals=[],
        )
    except Exception as e:
        logger.exception("=== 工作流异常: incident=%s type=%s ===", incident_id, type(e).__name__)
        return AlertResponse(
            incident_id=incident_id,
            status="error",
            triage=TriageResult(),
            diagnosis=DiagnosisResult(summary=f"工作流异常: {e}"),
            proposals=[],
        )

    # 保存到数据库
    await _save_to_db(result)

    # 构建响应
    proposals = [
        ProposalResult(
            plugin_name=p.get("plugin_name", ""),
            description=p.get("description"),
            risk_level=p.get("risk_level"),
            expected_outcome=p.get("expected_outcome"),
            args=p.get("args", {}),
        )
        for p in result.get("proposals", [])
    ]

    return AlertResponse(
        incident_id=result.get("incident_id", incident_id),
        status=result.get("final_status") or "completed",
        triage=TriageResult(
            category=result.get("category"),
            severity=result.get("severity"),
            service=result.get("service"),
        ),
        diagnosis=DiagnosisResult(
            summary=result.get("diagnosis_summary"),
            confidence=result.get("confidence"),
            evidence=result.get("evidence", {}),
            similar_incidents=result.get("similar_incidents", []),
        ),
        proposals=proposals,
        llm_turns=[
            LLMTurnResult(
                phase=t.get("phase", ""),
                turn_index=t.get("turn_index", 0),
                role=t.get("role", ""),
                content=t.get("content", ""),
                tool_name=t.get("tool_name"),
                tool_input=t.get("tool_input"),
            )
            for t in result.get("llm_turns", [])
        ],
        execution_results=result.get("execution_results", []),
        raw_workflow_state=_sanitize_state(result),
    )


async def _save_to_db(result: GraphState) -> None:
    """将工作流结果保存到数据库。"""
    try:
        async with session_scope() as session:
            incident_id = result.get("incident_id")

            # 检查是否已存在
            existing_result = await session.execute(
                select(Incident).where(Incident.id == str(incident_id))
            )
            existing = existing_result.scalar_one_or_none()

            if existing:
                # 更新已有记录
                existing.status = result.get("final_status") or existing.status
                existing.category = result.get("category") or existing.category
                existing.service = result.get("service") or existing.service
                existing.severity = result.get("severity") or existing.severity
                existing.summary = (result.get("diagnosis_summary") or existing.summary or "")[
                    :1024
                ]
                existing.llm_cost_tokens = result.get("llm_cost_tokens", 0)
                incident = existing
                logger.info("Incident 已存在，更新: %s", incident_id)
            else:
                # 创建新记录
                incident = Incident(
                    id=incident_id,
                    fingerprint=result.get("raw_alert", "")[:64],
                    status=result.get("final_status") or "completed",
                    category=result.get("category"),
                    service=result.get("service"),
                    severity=result.get("severity"),
                    summary=(result.get("diagnosis_summary") or "")[:1024],
                    raw_alert={"text": result.get("raw_alert", "")},
                    llm_cost_tokens=result.get("llm_cost_tokens", 0),
                )
                session.add(incident)

            # 保存 Diagnosis
            if result.get("diagnosis_summary"):
                diagnosis = Diagnosis(
                    incident_id=incident.id,
                    root_cause=result["diagnosis_summary"][:2048],
                    confidence=result.get("confidence", 0),
                    evidence=[result.get("evidence", {})],
                )
                session.add(diagnosis)

            # 保存 Proposals
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

            # 保存 LLM 对话轮次
            from app.db.models.llm_turn import LLMTurn

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


def _sanitize_state(state: GraphState) -> dict[str, Any]:
    """清理状态中的不可序列化字段。"""
    safe_keys = [
        "incident_id",
        "trace_id",
        "category",
        "severity",
        "service",
        "is_duplicate",
        "diagnosis_summary",
        "confidence",
        "final_status",
        "llm_cost_tokens",
    ]
    result = {k: state.get(k) for k in safe_keys}
    # diagnosis_messages 只保留文本内容
    msgs = state.get("diagnosis_messages", [])
    result["diagnosis_messages_count"] = len(msgs)
    return result
